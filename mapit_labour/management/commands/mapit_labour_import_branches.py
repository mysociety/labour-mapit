from pprint import pprint
from csv import DictReader
from re import T
from sqlite3 import IntegrityError

from django.core.management.base import LabelCommand
from django.db import transaction

from mapit.models import Area, Type, CodeType, Generation


class Command(LabelCommand):
    help = "Imports UK UPRNs from AddressBase Core"
    label = "<AddressBase Core CSV file>"

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "--commit",
            action="store_true",
            dest="commit",
            default=False,
            help="Commit changes to database",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            dest="purge",
            default=False,
            help="Delete all existing LBR areas first",
        )

    @transaction.atomic
    def handle_label(self, label: str, **options):
        if options["purge"]:
            Area.objects.filter(type__code="LBR").delete()

        with open(label, encoding="utf-8-sig") as f:
            self.handle_rows(DictReader(f))

        if not options["commit"]:
            transaction.set_rollback(True)

    def validate_row(self, row: dict, branch: dict):
        for k, v in row.items():
            # every field must have a value
            if not v:
                raise ValueError(f"Value for field {k} is missing")
        if row["area_type"] != "LBR":
            raise ValueError(
                f"Field area_type has an invalid value ('{row['area_type']}'), must be 'LBR'"
            )
        for key in ["parent_gss_code", "area_id", "area_name"]:
            # check that this row's common fields are consistent with
            # previous rows for this branch
            if branch[key] != row[key]:
                raise ValueError(
                    f"Field {key} value ('{row[key]}') doesn’t match expected value ('{branch[key]}')"
                )

    def handle_rows(self, csv: DictReader):
        # XXX do the right thing with generations
        generation = Generation.objects.current()
        gss_codetype = CodeType.objects.get(code="gss")
        lbr_codetype = CodeType.objects.get(code="lbr")

        branches = {}
        for i, row in enumerate(csv, start=2):
            branch = branches.setdefault(row["area_gss"], {**row, "subareas": []})
            try:
                self.validate_row(row, branch)
            except Exception as e:
                raise ValueError(f"Invalid row on line {i}: {e}")
            try:
                branch["subareas"].append(
                    Area.objects.get(
                        codes__type=gss_codetype, codes__code=row["gss_code"]
                    )
                )
            except Area.DoesNotExist:
                print(
                    f"Invalid row on line {i}: Subarea with GSS code '{row['gss_code']}' doesn't exist."
                )

        for branch in branches.values():
            a = Area.objects.create(
                name=branch["area_name"],
                type=Type.objects.get(code=branch["area_type"]),
                generation_high=generation,
                generation_low=generation,
            )
            a.codes.update_or_create(
                type=gss_codetype, defaults={"code": branch["area_gss"]}
            )
            a.codes.update_or_create(
                type=lbr_codetype, defaults={"code": branch["area_id"]}
            )
            try:
                a.parent_area = Area.objects.get(
                    codes__type=gss_codetype, codes__code=branch["parent_gss_code"]
                )
                a.save()
            except Area.DoesNotExist:
                print(
                    f"Parent area with GSS code '{branch['parent_gss_code']}' does not exist."
                )
                a.delete()
                continue
            for subarea in branch["subareas"]:
                for p in subarea.polygons.all():
                    p = p.polygon
                    for parent_poly in a.parent_area.polygons.all():
                        # buffering by zero will remove any non-polygon geometries
                        # (e.g. LineStrings/MultiLineStrings where the subarea only borders
                        # the parent geometry but doesn't actually overlap)
                        p = p.intersection(parent_poly.polygon).buffer(0.0)
                    if not p.empty:
                        a.polygons.create(polygon=p)
