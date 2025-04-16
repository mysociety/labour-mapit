from itertools import groupby
from collections import deque
from contextlib import contextmanager
import gzip
import bz2
import codecs
import io
import json
import sys
import time

from django.conf import settings
from django.core.management.base import LabelCommand
from django.db import transaction, connection

from csv import DictReader, writer


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
    uncompressed, or STDIN.
    """

    if path == "-":
        fin = codecs.getreader("utf_8_sig")(sys.stdin.buffer, errors="replace")
        yield fin
        return

    openers = {
        "gz": gzip.open,
        "bz2": bz2.open,
    }
    opener = openers.get(path.split(".")[-1], open)
    with opener(path, **kwargs) as f:
        yield f


# From https://stackoverflow.com/a/20260030
def iterable_to_stream(iterable, buffer_size=io.DEFAULT_BUFFER_SIZE):
    """
    Lets you use an iterable (e.g. a generator) that yields bytestrings as a read-only
    input stream. For efficiency, the stream is buffered.
    """

    class IterStream(io.RawIOBase):
        def __init__(self):
            self.leftover = None

        def readable(self):
            return True

        def readinto(self, b):
            try:
                ll = len(b)  # We're supposed to return at most this much
                chunk = self.leftover or next(iterable)
                output, self.leftover = chunk[:ll], chunk[ll:]
                b[: len(output)] = output
                return len(output)
            except StopIteration:
                return 0  # indicate EOF

    return io.BufferedReader(IterStream(), buffer_size=buffer_size)


def filter_old_rows(csv, cutoff):
    for row in csv:
        if row["LAST_UPDATE_DATE"] > cutoff:
            yield row


def process_row(row):
    row = {k.lower(): v for k, v in row.items()}
    row = (
        row["uprn"],
        row["postcode"].replace(" ", ""),
        row["easting"],
        row["northing"],
        row["single_line_address"],
        json.dumps(row),
    )
    f = io.StringIO()
    writer(f).writerow(row)
    row = f.getvalue()
    row = row.encode()
    return row


class Command(LabelCommand):
    help = "Imports UK UPRNs from AddressBase Core"
    label = "<AddressBase Core CSV file>"

    batch_size = 1000
    purge = False
    dry_run = False
    incremental = False

    def add_arguments(self, parser):
        super().add_arguments(parser)

        # can't specify --purge and --incremental at the same time
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--incremental",
            action="store_true",
            dest="incremental",
            default=self.incremental,
            help="Only process rows whose LAST_UPDATE_DATE is after the most recent already in the DB",
        )
        group.add_argument(
            "--purge",
            action="store_true",
            dest="purge",
            default=self.purge,
            help="Purge all existing UPRNs and import afresh",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=self.dry_run,
            help="Don't commit changes to database",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=self.batch_size,
            help=f"Batch size for bulk INSERT/UPDATE operations. Default {self.batch_size}",
        )

    def handle_label(self, label: str, **options):
        self.purge = options["purge"]
        self.incremental = options["incremental"]
        self.batch_size = options["batch_size"]
        self.dry_run = options["dry_run"]

        with open_compressed_maybe(label, mode="rt", encoding="utf-8-sig") as f:
            self.handle_start(DictReader(f))

    def handle_start(self, csv: DictReader):
        if self.purge and not self.dry_run:
            UPRN.objects.all().delete()

        if self.incremental:
            # query the DB to find when the most recent update was
            self.stdout.write(
                "Ignoring CSV rows last updated on or before: ",
                ending="",
            )
            self.stdout.flush()
            cutoff = UPRN.objects.values_list("addressbase", flat=True).order_by(
                "-addressbase__last_update_date"
            )[0]["last_update_date"]
            print(f"{cutoff}", file=self.stdout)
            csv = filter_old_rows(csv, cutoff)

        self.count = {
            "total": 0,
            "created": 0,
            "updated": 0,
        }

        cursor = connection.cursor()
        cursor.execute(
            "CREATE TEMPORARY TABLE mapit_labour_uprn_new "
            "(uprn bigint, postcode varchar(7), location geometry(Point, 27700), easting float, northing float, single_line_address text, addressbase jsonb) "
            "ON COMMIT DELETE ROWS"
        )

        i = 0
        start = time.time()
        for rows in batched(csv, self.batch_size):
            i += 1
            self.handle_rows(rows)
            dur = time.time() - start
            self.stdout.write(
                f"\rBatch {i}, {dur:.0f}s, {i/dur:.1f} batch/s, {self.count['total']/dur:.1f} row/s, {self.count['created']} created, {self.count['updated']} updated, {self.count['total']} total",
                ending="",
            )
        print("", file=self.stdout)

        cursor.execute("DROP TABLE mapit_labour_uprn_new")

    def handle_rows(self, csv):
        csv = map(process_row, csv)
        csv = iterable_to_stream(csv)

        with transaction.atomic():
            cursor = connection.cursor()
            cursor.copy_expert(
                "COPY mapit_labour_uprn_new(uprn, postcode, easting, northing, single_line_address, addressbase) "
                "FROM STDIN WITH (FORMAT csv)",
                csv,
            )
            self.count["total"] += cursor.rowcount
            cursor.execute(
                "UPDATE mapit_labour_uprn_new SET location = ST_SetSRID(ST_Point(easting, northing), 27700)"
            )
            cursor.execute(
                "UPDATE mapit_labour_uprn SET postcode = n.postcode, location = n.location, single_line_address = n.single_line_address, addressbase = n.addressbase "
                "FROM mapit_labour_uprn_new n "
                "WHERE n.addressbase IS DISTINCT FROM mapit_labour_uprn.addressbase AND n.uprn = mapit_labour_uprn.uprn"
            )
            self.count["updated"] += cursor.rowcount
            cursor.execute(
                "INSERT INTO mapit_labour_uprn (uprn, postcode, location, single_line_address, addressbase) "
                "SELECT n.uprn, n.postcode, n.location, n.single_line_address, n.addressbase FROM mapit_labour_uprn_new n "
                "LEFT JOIN mapit_labour_uprn p ON n.uprn = p.uprn WHERE p.uprn IS NULL"
            )
            self.count["created"] += cursor.rowcount
            transaction.set_rollback(self.dry_run)
