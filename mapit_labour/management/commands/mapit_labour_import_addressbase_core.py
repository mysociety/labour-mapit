from itertools import groupby
from typing import Dict

from django.core.management.base import LabelCommand
from django.contrib.gis.geos import Point
from django.db import transaction, IntegrityError

from csv import DictReader


from mapit_labour.models import UPRN


class Command(LabelCommand):
    help = "Imports UK UPRNs from AddressBase Core"
    label = "<AddressBase Core CSV file>"

    count = {}  # initialised in handle()
    batch_size = 1000
    purge = False

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "--purge",
            action="store_true",
            dest="purge",
            default=False,
            help="Purge all existing UPRNs and import afresh",
        )

    def handle_label(self, label: str, **options):
        self.purge = options["purge"]

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

            for _, uprns in groupby(
                (self.create_uprn(row) for row in csv),
                lambda _: self.count["total"] // self.batch_size,
            ):
                with transaction.atomic():
                    UPRN.objects.bulk_create(uprns)
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
