from csv import DictReader

from django.db import transaction

from mapit.models import Area, Type, CodeType, Generation

REQUIRED_CSV_FIELDS = {
    "area_type",
    "area_id",
    "area_name",
    "area_gss",
    "gss_code",
    "parent_gss_code",
}


class BranchCSVImporter:
    commit = False
    purge = False
    path = None
    generation = None

    created = 0
    updated = 0
    warnings = None
    error = None

    def __init__(self, path, purge=False, commit=False, generation=None):
        self.path = path
        self.purge = purge
        self.commit = commit

        if not generation:
            self.generation = Generation.objects.current()
        else:
            try:
                self.generation = Generation.objects.get(generation)
            except Generation.DoesNotExist:
                raise ValueError("Invalid generation number specified")

        self.warnings = []

    @classmethod
    def import_from_csv(cls, path, purge, commit, generation):
        importer = BranchCSVImporter(
            path, purge=purge, commit=commit, generation=generation
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
            Area.objects.filter(type__code="LBR").delete()

        try:
            with open(self.path, encoding="utf-8-sig") as f:
                reader = DictReader(f)
                self.validate_fieldnames(reader.fieldnames)
                self.handle_rows(reader)
        except Exception as e:
            self.error = str(e)

        if not self.commit:
            transaction.set_rollback(True)

    def validate_fieldnames(self, fieldnames):
        if not set(fieldnames) >= REQUIRED_CSV_FIELDS:
            raise Exception(
                f"Invalid CSV header. Required fields are: {', '.join(REQUIRED_CSV_FIELDS)}"
            )

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
        gss_codetype = CodeType.objects.get(code="gss")
        lbr_codetype = CodeType.objects.get(code="lbr")

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
            parent_gss_codes.add(row["parent_gss_code"])

        parents = self._load_parents(parent_gss_codes)

        for branch in branches.values():
            parent_area = parents.get(branch["parent_gss_code"])
            if not parent_area:
                continue
            # TODO handle updating existing branches
            a = Area.objects.create(
                name=branch["area_name"],
                type=Type.objects.get(code=branch["area_type"]),
                # XXX do the right thing with generations
                generation_high=self.generation,
                generation_low=self.generation,
                parent_area=parent_area,
            )
            self.created += 1
            a.codes.update_or_create(
                type=gss_codetype, defaults={"code": branch["area_gss"]}
            )
            a.codes.update_or_create(
                type=lbr_codetype, defaults={"code": branch["area_id"]}
            )
            has_geometry = False
            area_area = 0  # for measuring the geographic area of this area's geometries
            for subarea in branch["subareas"]:
                for p in subarea.polygons.all():
                    p = p.polygon
                    for parent_poly in a.parent_area.polygons.all():
                        # buffering by zero will remove any non-polygon geometries
                        # (e.g. LineStrings/MultiLineStrings where the subarea only borders
                        # the parent geometry but doesn't actually overlap)
                        p = p.intersection(parent_poly.polygon).buffer(0.0)
                    if p.empty:
                        continue
                    # Sometimes the intersection results in a MultiPolygon, which
                    # we'll need to store as separate Polygon geometries
                    if p.geom_type == "MultiPolygon":
                        for poly in p:
                            a.polygons.create(polygon=poly)
                            has_geometry = True
                            area_area += poly.area
                    else:
                        a.polygons.create(polygon=p)
                        has_geometry = True
                        area_area += p.area
            if not has_geometry:
                self.warnings.append(
                    f"Area {a.id} (branch {branch['area_id']}) has no geometry"
                )
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
