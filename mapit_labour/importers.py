from csv import DictReader

from django.db import transaction
from django.contrib.gis.geos import MultiPolygon

from mapit.models import Area, Type, CodeType, Generation

from .models import CSVImportTaskProgress

REQUIRED_CSV_FIELDS = {
    "area_type",
    "area_id",
    "area_name",
    "area_gss",
    "gss_code",
    "parent_gss_code",
}

BRANCH_CODE = {"LBR", "LBRF"}
REGION_CODE = "LR"
VALID_CODES = BRANCH_CODE | {REGION_CODE}


class BranchCSVImporter:
    commit = False
    purge = False
    path = None
    generation = None

    created = 0
    updated = 0
    warnings = None
    error = None

    progress = None

    def __init__(
        self,
        path,
        purge=False,
        commit=False,
        generation=None,
        generation_description=None,
        progress_id=None,
    ):
        self.path = path
        self.purge = purge
        self.commit = commit

        if not generation:
            self.generation = Generation.objects.current()
        elif generation == "new":
            self.generation = Generation.objects.create(
                description=generation_description
            )
        else:
            try:
                self.generation = Generation.objects.get(id=int(generation))
            except Generation.DoesNotExist:
                raise ValueError("Invalid generation number specified")

        if progress_id:
            try:
                self.progress = CSVImportTaskProgress.objects.get(id=progress_id)
            except CSVImportTaskProgress.DoesNotExist:
                pass

        self.warnings = []

    @classmethod
    def import_from_csv(
        cls,
        path,
        purge,
        commit,
        generation,
        generation_description=None,
        progress_id=None,
    ):
        importer = BranchCSVImporter(
            path,
            purge=purge,
            commit=commit,
            generation=generation,
            generation_description=generation_description,
            progress_id=progress_id,
        )
        importer.do_import()
        return {
            "created": importer.created,
            "updated": importer.updated,
            "warnings": importer.warnings,
            "error": importer.error,
        }

    @transaction.atomic
    def do_import(self):
        if self.purge:
            Area.objects.filter(type__code__in=VALID_CODES).delete()

        try:
            with open(self.path, encoding="utf-8-sig") as f:
                reader = DictReader(f)
                self.validate_fieldnames(reader.fieldnames)
                self.handle_rows(reader)
        except Exception as e:
            self.error = str(e)

        if not self.commit:
            transaction.set_rollback(True)

    def update_progress(self, msg):
        if not self.progress:
            return

        self.progress.progress = msg
        # Use the second DB connection as we're in a transaction on the
        # default connection so changes to the CSVImportTaskProgress model
        # won't be persisted.
        self.progress.save(using="logging")

    def validate_fieldnames(self, fieldnames):
        if not set(fieldnames) >= REQUIRED_CSV_FIELDS:
            raise Exception(
                f"Invalid CSV header. Required fields are: {', '.join(REQUIRED_CSV_FIELDS)}"
            )

    def validate_row(self, row: dict, branch: dict):
        if row["area_type"] not in VALID_CODES:
            raise ValueError(
                f"Field area_type has an invalid value ('{row['area_type']}'), must be one of: {', '.join(VALID_CODES)}"
            )
        for k, v in row.items():
            # every field must have a value (except LR areas - they must have an empty parent_gss_code)
            if k == "parent_gss_code" and branch["area_type"] == REGION_CODE:
                if v:
                    raise ValueError(
                        f"Regions must not have a parent_gss_code specified."
                    )
            elif not v:
                raise ValueError(f"Value for field {k} is missing")
        for key in ["parent_gss_code", "area_id", "area_name"]:
            # check that this row's common fields are consistent with
            # previous rows for this branch
            if branch[key] != row[key]:
                raise ValueError(
                    f"Field {key} value ('{row[key]}') doesn’t match expected value ('{branch[key]}')"
                )
        # Must ensure there isn't already a non-Labour area using this GSS code
        if (
            Area.objects.filter(codes__code=row["area_gss"])
            .exclude(codes__type__code__in={c.lower() for c in VALID_CODES})
            .exists()
        ):
            raise ValueError(
                f"Cannot reuse an existing GSS code for region/branch: '{row['area_gss']}'"
            )

    def handle_rows(self, csv: DictReader):
        gss_codetype = CodeType.objects.get(code="gss")
        codetypes = {k: CodeType.objects.get(code=k.lower()) for k in VALID_CODES}
        areatypes = {k: Type.objects.get(code=k) for k in VALID_CODES}

        self.update_progress("Parsing/validating CSV file")
        branches = {}
        parent_gss_codes = set()
        for i, row in enumerate(csv, start=2):
            branch = branches.setdefault(row["area_gss"], {**row, "subareas": []})
            try:
                self.validate_row(row, branch)
            except Exception as e:
                raise ValueError(f"Invalid row on line {i}: {e}")
            try:
                branch["subareas"].append(
                    Area.objects.prefetch_related("polygons").get(
                        codes__type=gss_codetype, codes__code=row["gss_code"]
                    )
                )
            except Area.DoesNotExist:
                self.warnings.append(
                    f"Invalid row on line {i}: Subarea with GSS code '{row['gss_code']}' doesn't exist."
                )
            if parent_gss_code := row["parent_gss_code"]:
                parent_gss_codes.add(parent_gss_code)

        self.update_progress("Loading parent areas")
        parents = self._load_parents(parent_gss_codes)
        branch_count = len(branches)
        for i, branch in enumerate(branches.values(), start=1):
            self.update_progress(f"Working on area {i} of {branch_count}")
            parent_area = parents.get(branch["parent_gss_code"])

            try:
                if self.purge:
                    # save a DB query if we know it's not going to be there
                    raise Area.DoesNotExist
                a = Area.objects.get(
                    codes__type=gss_codetype, codes__code=branch["area_gss"]
                )
                a.name = branch["area_name"]
                # XXX do the right thing with generations
                a.generation_high = self.generation
                if parent_area and a.parent_area != parent_area:
                    self.warnings.append(f"Branch {branch['area_id']} changed parent")
                    a.parent_area = parent_area
                a.save()
                # XXX probably don't want to delete them all here, instead
                # need to somehow check if they've changed and if so
                # create a brand new area in the current generation
                a.polygons.all().delete()
                self.updated += 1
            except Area.DoesNotExist:
                a = Area.objects.create(
                    name=branch["area_name"],
                    type=areatypes[branch["area_type"]],
                    generation_high=self.generation,
                    generation_low=self.generation,
                    parent_area=parent_area,
                )
                self.created += 1

            a.codes.update_or_create(
                type=gss_codetype, defaults={"code": branch["area_gss"]}
            )
            a.codes.update_or_create(
                type=codetypes[branch["area_type"]],
                defaults={"code": branch["area_id"]},
            )
            has_geometry = False
            area_area = 0  # for measuring the geographic area of this area's geometries

            # It's much faster to gather all the geometries for the parent area
            # (if there is one) and all subareas into MultiPolygons and then
            # intersect them in one go
            subs_polys = []
            for subarea in branch["subareas"]:
                subs_polys.extend((p.polygon for p in subarea.polygons.all()))
            branch_poly = MultiPolygon(subs_polys)
            if parent_area:
                parent_multi = MultiPolygon(
                    [p.polygon for p in a.parent_area.polygons.all()]
                )
                branch_poly = parent_multi.intersection(branch_poly)
            # buffering by zero will remove any non-polygon geometries
            # (e.g. LineStrings/MultiLineStrings where the subarea only borders
            # a parent geometry but doesn't actually overlap)
            branch_poly = branch_poly.buffer(0.0)
            if not branch_poly.empty:
                # If the above processing results in a MultiPolygon
                # we'll need to store it as separate Polygon geometries
                if branch_poly.geom_type == "MultiPolygon":
                    for poly in branch_poly:
                        a.polygons.create(polygon=poly)
                        has_geometry = True
                        area_area += poly.area
                else:
                    a.polygons.create(polygon=branch_poly)
                    has_geometry = True
                    area_area += branch_poly.area
            if not has_geometry:
                self.warnings.append(
                    f"Branch {branch['area_id']} doesn't overlap with parent area ({branch['parent_gss_code']}), not creating."
                )
                a.delete()
            elif area_area < 50000:
                self.warnings.append(
                    f"Area {a.id} (branch {branch['area_id']}) has a small geographic area ({int(area_area)} ㎡)"
                )

    def _load_parents(self, gss_codes):
        gss_codetype = CodeType.objects.get(code="gss")

        parents = {}
        for area in Area.objects.prefetch_related("polygons").filter(
            codes__type=gss_codetype, codes__code__in=gss_codes
        ):
            parents[area.codes.get(type=gss_codetype).code] = area

        for gss_code in gss_codes:
            if not parents.get(gss_code):
                self.warnings.append(
                    f"Parent area with GSS code '{gss_code}' does not exist."
                )

        return parents
