from itertools import groupby, islice
from typing import Dict
from collections import deque

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
    connection.queries_log = deque(maxlen=0)


def batched(iterable, size):
    """
    Split an iterable into smaller iterables no bigger than size
    """
    return (
        (g for _, g in item)
        for _, item in groupby(enumerate(iterable), key=lambda x: x[0] // size)
    )


class Command(LabelCommand):
    help = "Imports UK UPRNs from AddressBase Core"
    label = "<AddressBase Core CSV file>"

    count = {}  # initialised in handle()
    batch_size = 1000
    purge = False
    limit = 0

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
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

        with open(label, encoding="utf-8-sig") as f:
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
                with transaction.atomic():
                    UPRN.objects.bulk_create(self.create_uprn(row) for row in rows)
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

    def print_stats(self):
        c = self.count
        print(f"Imported {c['total']} ({c['created']} new, {c['updated']} updated)")
