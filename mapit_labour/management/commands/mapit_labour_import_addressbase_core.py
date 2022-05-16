from itertools import groupby, islice
from typing import Dict
from collections import deque
from contextlib import contextmanager
import gzip
import bz2

from django.conf import settings
from django.core.management.base import LabelCommand
from django.contrib.gis.geos import Point
from django.db import transaction, connection

from csv import DictReader


from mapit_labour.models import UPRN

if settings.DEBUG:
    # Disable the Django SQL query log, which eats memory.
    # It's normally cleared after a request but we're not
    # running in a request-response cycle here so it just keeps
    # growing and will cause problems when importing this much data.
    connection.queries_log = deque(maxlen=0)  # pragma: no cover


def batched(iterable, size):
    """
    Split an iterable into smaller iterables no bigger than size
    """
    return (
        (g for _, g in item)
        for _, item in groupby(enumerate(iterable), key=lambda x: x[0] // size)
    )


@contextmanager
def open_compressed_maybe(path, **kwargs):
    """
    Helper function to abstract away opening a file that may be GZip, BZ2 or
    uncompressed.
    """
    openers = {
        "gz": gzip.open,
        "bz2": bz2.open,
    }
    opener = openers.get(path.split(".")[-1], open)
    with opener(path, **kwargs) as f:
        yield f


class Command(LabelCommand):
    help = "Imports UK UPRNs from AddressBase Core"
    label = "<AddressBase Core CSV file>"

    count = {}  # initialised in handle()
    batch_size = 1000
    purge = False
    limit = 0

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--purge",
            action="store_true",
            dest="purge",
            default=self.purge,
            help="Purge all existing UPRNs and import afresh",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=self.batch_size,
            help=f"Batch size for bulk INSERT/UPDATE operations. Default {self.batch_size}",
        )
        parser.add_argument(
            "--limit",
            dest="limit",
            type=int,
            default=self.limit,
            help="Stop after importing this many rows from the CSV. 0 (default) for no limit.",
        )

    def handle_label(self, label: str, **options):
        self.purge = options["purge"]
        self.batch_size = options["batch_size"]
        self.limit = options["limit"]

        with open_compressed_maybe(label, mode="rt", encoding="utf-8-sig") as f:
            self.handle_rows(DictReader(f))

    def handle(self, *args, **kwargs):
        self.count = {
            "total": 0,
            "created": 0,
            "updated": 0,
        }
        super().handle(*args, **kwargs)

    def handle_rows(self, csv: DictReader):
        if self.purge:
            UPRN.objects.all().delete()

        for rows in batched(islice(csv, self.limit or None), self.batch_size):
            if self.purge:
                new, existing = rows, []
            else:
                new, existing = self.find_existing_uprns(rows)
            if new:
                with transaction.atomic():
                    UPRN.objects.bulk_create(self.create_uprn(row) for row in new)
            if existing:
                self.update_existing_uprns(existing)
            self.print_stats()
        self.print_stats()

    def create_uprn(self, row: Dict[str, str]):
        row = {k.lower(): v for k, v in row.items()}

        self.count["total"] += 1
        self.count["created"] += 1
        return UPRN(
            uprn=row["uprn"],
            postcode=row["postcode"].replace(" ", ""),
            location=Point(float(row["easting"]), float(row["northing"]), srid=27700),
            single_line_address=row["single_line_address"],
            addressbase=row,
        )

    def find_existing_uprns(self, rows):
        """
        Takes a list of rows from the CSV and divides them into two lists which
        are returned: those that don't already exist as URPN objects in the DB
        and those that do.
        """
        # need to consume this iterator now because we use it twice below
        rows = list(rows)
        db_uprns = {
            u.uprn: u for u in UPRN.objects.filter(uprn__in=(r["UPRN"] for r in rows))
        }
        existing = []
        new = []
        for row in rows:
            uprn = int(row["UPRN"])
            if uprn in db_uprns:
                existing.append((row, db_uprns[uprn]))
            else:
                new.append(row)
        return new, existing

    def update_existing_uprns(self, rows):
        """
        Takes a list of rows from the CSV that correspond to UPRNs already
        in the DB and updates them accordingly.
        """
        for row, uprn in rows:
            row = {k.lower(): v for k, v in row.items()}
            uprn.postcode = row["postcode"].replace(" ", "")
            uprn.location = Point(
                float(row["easting"]), float(row["northing"]), srid=27700
            )
            uprn.single_line_address = row["single_line_address"]
            uprn.addressbase = row
            self.count["total"] += 1
            self.count["updated"] += 1

        with transaction.atomic():
            UPRN.objects.bulk_update(
                [u[1] for u in rows],
                ["postcode", "location", "single_line_address", "addressbase"],
            )

    def print_stats(self):
        c = self.count
        self.stdout.write(
            f"Imported {c['total']} ({c['created']} new, {c['updated']} updated)",
        )
