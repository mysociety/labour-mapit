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
    often = 1000
    purge = False

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--purge",
            action="store_true",
            dest="purge",
            default=False,
            help="Purge all existing UPRNs and import afresh",
        )

    def handle_label(self, label: str, **options):
        self.purge = options["purge"]

        if self.purge:
            UPRN.objects.all().delete()
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
        for row in csv:
            self.handle_row(row)

            if self.count["total"] % self.often == 0:
                self.print_stats()
        self.print_stats()

    def handle_row(self, row: Dict[str, str]):
        row = {k.lower(): v for k, v in row.items()}
        e = float(row["easting"])
        n = float(row["northing"])
        location = Point(e, n, srid=27700)
        postcode = row["postcode"].replace(" ", "")
        uprn = row["uprn"]

        if self.purge:
            UPRN.objects.create(
                uprn=uprn,
                postcode=postcode,
                location=location,
                addressbase=row,
            )
            self.count["created"] += 1
        else:
            _, created = UPRN.objects.update_or_create(
                uprn=uprn,
                defaults=dict(
                    postcode=postcode,
                    location=location,
                    addressbase=row,
                ),
            )
            self.count["created" if created else "updated"] += 1
        self.count["total"] += 1

    def print_stats(self):
        c = self.count
        print(f"Imported {c['total']} ({c['created']} new, {c['updated']} updated)")
