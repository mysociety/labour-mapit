import csv
import os

from django.conf import settings
from django.contrib.gis.geos import Polygon
from mapit.models import Area, Code, CodeType, Generation, Geometry, Type


def _code_type(code):
    v, _ = CodeType.objects.get_or_create(code=code)
    return v


def _area_type(code):
    v, _ = Type.objects.get_or_create(code=code)
    return v


def _fixtures_dir():
    return os.path.join(settings.BASE_DIR, "mapit_labour", "tests", "fixtures")


def gss_code_type():
    return _code_type("gss")


def labour_region_code_type():
    return _code_type("lr")


def labour_branch_code_type():
    return _code_type("lbr")


def labour_branch_f_code_type():
    return _code_type("lbrf")


def labour_region_area_type():
    return _area_type("LR")


def labour_branch_area_type():
    return _area_type("LBR")


def labour_branch_f_area_type():
    return _area_type("LBRF")


def non_labour_area_type():
    return _area_type("non_labour")


def current_generation():
    if Generation.objects.current():
        return Generation.objects.current()
    return Generation.objects.create(active=True, description="current")


def create_area(x, y, width, area_type, codes, parent=None):
    a = Area.objects.create(type=area_type, parent_area=parent)
    for type_, code in codes:
        Code.objects.create(type=type_, code=code, area=a)
    Geometry.objects.create(
        area=a, polygon=Polygon.from_bbox((x, y, x + width, y + width))
    )
    return a


class Base(object):
    purge = False
    commit = True
    csv_field_names = (
        "area_type",
        "area_id",
        "area_name",
        "area_gss",
        "gss_code",
        "parent_gss_code",
    )
    csv_path_override = None
    generation_id = None
    generation_description = None

    def csv_rows(self):
        return []

    def setup_models(self):
        return

    def is_result_correct(self, result):
        return True, []

    def are_models_correct(self):
        return True, []

    def is_exception_correct(self, exception):
        return False, "Expected no exception, got " + str(exception)

    def setUp(self):
        csv_path = os.path.join(_fixtures_dir(), self.__class__.__name__ + ".csv")
        with open(csv_path, "w") as f:
            writer = csv.DictWriter(f, self.csv_field_names)
            writer.writeheader()
            for row in self.csv_rows():
                writer.writerow(row)
        self.csv_path = csv_path

        gss_code_type()
        labour_region_code_type()
        labour_branch_code_type()
        labour_branch_f_code_type()
        labour_region_area_type()
        labour_branch_area_type()
        labour_branch_f_area_type()
        current_generation()

        self.setup_models()

    def test(self):
        try:
            result = self.execute(
                commit=self.commit,
                purge=self.purge,
                csv_path=self.csv_path_override or self.csv_path,
                generation_id=self.generation_id,
                generation_description=self.generation_description,
            )
        except Exception as e:
            exception_ok, error = self.is_exception_correct(e)
            if not exception_ok:
                self.fail("Exception incorrect: " + error)
            return

        result_ok, result_errors = self.is_result_correct(result)
        if not result_ok:
            self.fail("Result incorrect: " + ", ".join(result_errors))

        models_ok, model_errors = self.are_models_correct()
        if not models_ok:
            self.fail("Post-run models are incorrect: " + ", ".join(model_errors))

    def tearDown(self):
        os.remove(self.csv_path)


class ShouldThrow:
    def is_exception_correct(self, e):
        if (
            type(e) == type(self.expected_exception)
            and e.args == self.expected_exception.args
        ):
            return True, ""
        return False, f"Expected {self.expected_exception} got {e}"


class ShouldError:
    def is_result_correct(self, result):
        error = result["error"]
        if not error:
            return False, ["expected an error but none returned"]
        if not self.is_error_correct(error):
            return False, ["error message not as expected, got: " + error]
        return True, []


class ShouldSucceed:
    expected_warning_substring = None
    expected_updates = 0
    expected_creations = 0
    expected_areas_count = 0
    expected_area_values_by_gss = {}

    def is_result_correct(self, result):
        success = True
        errors = []
        if result["error"]:
            success = False
            errors.append("did not expect an error but got " + result["error"])

        if self.expected_updates != result["updated"]:
            success = False
            errors.append(
                f"expected {self.expected_updates} updates, got {result['updated']}"
            )

        if self.expected_creations != result["created"]:
            success = False
            errors.append(
                f"expected {self.expected_creations} creations, got {result['created']}"
            )

        warnings = result["warnings"]
        if not self.expected_warning_substring and len(warnings) > 0:
            success = False
            errors.append(f"got unexpected warnings {warnings}")

        if self.expected_warning_substring:
            if len(warnings) > 1:
                success = False
                errors.append(
                    f"expected only one warning containing {self.expected_warning_substring}, got multiple {warnings}"
                )
            elif len(warnings) == 0:
                success = False
                errors.append(
                    f"expected warning containing {self.expected_warning_substring}, but got none"
                )
            else:
                warning = warnings[0]
                if self.expected_warning_substring not in warning:
                    success = False
                    errors.append(
                        f"warning {warning} did not contain {self.expected_warning_substring}"
                    )

        return success, errors

    def are_models_correct(self):
        success = True
        errors = []

        def _fail(message):
            global success
            success = False
            errors.append(message)

        areas_count = Area.objects.count()
        if areas_count != self.expected_areas_count:
            _fail(f"expected {self.expected_areas_count} areas, got {areas_count}")

        for gss_code, expected_values in self.expected_area_values_by_gss.items():
            error_prefix = f"expected area with GSS {gss_code} "

            area = Area.objects.filter(
                codes__code=gss_code, codes__type=gss_code_type()
            ).first()
            if not area:
                _fail(error_prefix + "not found")
                continue

            name = expected_values.get("name", "")
            if name and name != area.name:
                _fail(error_prefix + f"to have name {name}, got {area.name}")

            generation_high_id = expected_values.get("generation_high_id", "")
            if generation_high_id and area.generation_high.id != generation_high_id:
                _fail(
                    error_prefix
                    + f"to have generation high ID {generation_high_id}, got {area.generation_high.id}"
                )

            type_ = expected_values.get("type", "")
            if type_ and type_ != area.type:
                _fail(error_prefix + f"to have type {type_}, got {area.type}")

            area_area = expected_values.get("area", "")
            if area_area:
                actual_area_area = area.polygons.first().area
                if actual_area_area != area_area:
                    _fail(
                        error_prefix
                        + f"to have area {area_area}, got {actual_area_area}"
                    )

            parent_gss = expected_values.get("parent_gss", "")
            if parent_gss:
                if not area.parent_area:
                    _fail(
                        error_prefix
                        + f"to have parent area with GSS {parent_gss}, none found"
                    )
                else:
                    actual_parent_gss = area.parent_area.codes.filter(
                        type=gss_code_type()
                    ).first()
                    if not actual_parent_gss:
                        _fail(
                            error_prefix
                            + f"to have parent area with GSS {parent_gss}, parent found but has no GSS code"
                        )
                    elif actual_parent_gss != parent_gss:

                        _fail(
                            error_prefix
                            + f"to have parent area with GSS {parent_gss}, got {actual_parent_gss}"
                        )

            for key, code_type in {
                "lbr_code": labour_branch_code_type(),
                "lr_code": labour_region_code_type(),
            }.items():
                expected_code = expected_values.get(key, "")
                if expected_code:
                    actual_code = area.codes.filter(type=code_type).first()
                    if not actual_code:
                        _fail(
                            error_prefix + f"to have {key} {expected_code}, none found"
                        )
                    elif actual_code != expected_code:
                        _fail(
                            error_prefix
                            + f"to have {key} {expected_code}, got {actual_code}"
                        )

        return success, errors


class ThrowsWhenGenerationDoesNotExist(ShouldThrow, Base):
    generation_id = 100
    expected_exception = ValueError("Invalid generation number specified")


class ErrorsWhenCSVFileCantBeOpened(ShouldError, Base):
    csv_path_override = "fake-path"

    def is_error_correct(self, error):
        return "No such file or directory" in error


class ErrorsWhenCSVIsMissingRequiredFields(ShouldError, Base):
    csv_field_names = ()

    def is_error_correct(self, error):
        return all(
            [
                "Invalid CSV header. Required fields are:" in error,
                "area_type" in error,
                "area_id" in error,
                "area_name" in error,
                "area_gss" in error,
                "gss_code" in error,
                "parent_gss_code" in error,
            ]
        )


class ErrorsWhenUnknownAreaTypeGiven(ShouldError, Base):
    def csv_rows(self):
        return [
            {
                "area_type": "UNKNOWN",
            },
        ]

    def is_error_correct(self, error):
        return "Field area_type has an invalid value" in error


class ErrorsWhenRowIsMissingValueBase(ShouldError, Base):
    def csv_rows(self):
        row = {
            "area_type": "LBR",
            "area_id": "123",
            "area_name": "name",
            "area_gss": "123",
            "gss_code": "123",
            "parent_gss_code": "123",
        }
        del row[self.missing_field]
        return [row]

    def is_error_correct(self, error):
        return f"Value for field {self.missing_field} is missing" in error


class ErrorsWhenRowIsMissingAreaId(ErrorsWhenRowIsMissingValueBase):
    missing_field = "area_id"


class ErrorsWhenRowIsMissingAreaName(ErrorsWhenRowIsMissingValueBase):
    missing_field = "area_name"


class ErrorsWhenRowIsMissingAreaGSS(ErrorsWhenRowIsMissingValueBase):
    missing_field = "area_gss"


class ErrorsWhenRowIsMissingGSSCode(ErrorsWhenRowIsMissingValueBase):
    missing_field = "gss_code"


class ErrorsWhenRowIsMissingParentGSSCode(ErrorsWhenRowIsMissingValueBase):
    missing_field = "parent_gss_code"


class ErrorsWhenRegionHasParent(ShouldError, Base):
    def csv_rows(self):
        return [
            {
                "area_type": "LR",
                "area_id": "123",
                "area_name": "name",
                "area_gss": "123",
                "gss_code": "123",
                "parent_gss_code": "123",
            },
        ]

    def is_error_correct(self, error):
        return "Regions must not have a parent_gss_code specified." in error


class ErrorsWhenBranchDetailsAreInconsistentBase(ShouldError, Base):
    def csv_rows(self):
        row = {
            "area_type": "LBR",
            "area_id": "123",
            "area_name": "name",
            "area_gss": "123",
            "gss_code": "123",
            "parent_gss_code": "123",
        }
        row_2 = row.copy()
        row_2[self.inconsistent_field] = row[self.inconsistent_field] + "4"
        return [row, row_2]

    def is_error_correct(self, error):
        return (
            f"Field {self.inconsistent_field} value" in error
            and "doesn’t match expected value" in error
        )


class ErrorsWhenBranchAreaIdsAreInconsistent(
    ErrorsWhenBranchDetailsAreInconsistentBase
):
    inconsistent_field = "area_id"


class ErrorsWhenBranchParentGSSsAreInconsistent(
    ErrorsWhenBranchDetailsAreInconsistentBase
):
    inconsistent_field = "parent_gss_code"


class ErrorsWhenBranchAreaNamesAreInconsistent(
    ErrorsWhenBranchDetailsAreInconsistentBase
):
    inconsistent_field = "area_name"


class ErrorsWhenAreaAlreadyExistsForANonLabourEntity(ShouldError, Base):
    def csv_rows(self):
        return [
            {
                "area_type": "LR",
                "area_id": "123",
                "area_name": "name",
                "area_gss": "123",
                "gss_code": "123",
            },
        ]

    def setup_models(self):
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "123")],
        )

    def is_error_correct(self, error):
        return "Cannot reuse an existing GSS code for region/branch: '123'" in error


class HappyPathBase(ShouldSucceed, Base):
    expected_creations = 1
    expected_updates = 1
    expected_areas_count = 4
    expected_area_values_by_gss = {
        "LR_1": {
            "name": "region name",
            "type": labour_region_area_type(),
            "lr_code": "1",
        },
        "LBR_1": {
            "name": "branch name",
            "type": labour_region_area_type(),
            "lbr_code": "1",
            "parent_gss": "LR_1",
            "area": 70 * 500,  # branch area truncated to region
        },
    }

    def setup_models(self):
        # region area
        create_area(
            x=0,
            y=0,
            width=750,
            area_type=labour_region_area_type(),
            codes=[(gss_code_type(), "LR_1"), (labour_region_code_type(), "1")],
        )
        # branch subarea #1
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "101")],
        )
        # branch subarea #2
        create_area(
            x=500,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "102")],
        )

    def csv_rows(self):
        return [
            #  region
            {
                "area_type": "LR",
                "area_id": "1",
                "area_gss": "LR_1",
                "area_name": "region name",
                "gss_code": "LR_1",
            },
            # branch subarea #1
            {
                "area_type": "LBR",
                "area_id": "1",
                "area_gss": "LBR_1",
                "area_name": "branch name",
                "parent_gss_code": "LR_1",
                "gss_code": "101",
            },
            # branch subarea #2
            {
                "area_type": "LBR",
                "area_id": "1",
                "area_gss": "LBR_1",
                "area_name": "branch name",
                "parent_gss_code": "LR_1",
                "gss_code": "102",
            },
        ]


class SetsUpBranchesAndRegions(HappyPathBase):
    pass


class MakesNoChangesWhenCommitIsFalse(HappyPathBase):
    commit = False
    expected_area_values_by_gss = {}
    expected_area_count = 3


class UsesTheCurrentGenerationWhenNoneIsGiven(HappyPathBase):
    expected_area_values_by_gss = {
        "LR_1": {
            "generation_high": current_generation().id,
        },
    }


class SetsUpANewGenerationIfNewSpecified(HappyPathBase):
    generation_id = "new"
    generation_description = "next gen"
    expected_area_values_by_gss = {
        "LR_1": {
            "generation_high_id": current_generation().id + 1,
        },
    }

    def are_models_correct(self):
        next_gen = Generation.objects.filter(description="next gen").first()
        if not next_gen:
            return False, ["expected new generation not found"]
        return super().are_models_correct()


class UsesTheGivenGeneration(HappyPathBase):
    generation_id = 0
    expected_area_values_by_gss = {
        "LR_1": {
            "generation_high_id": 0,
        },
    }


class WarnsIfAreaIsSmall(ShouldSucceed, Base):
    expected_creations = 1
    expected_areas_count = 3
    expected_warning_substring = "has a small geographic area (100 ㎡)"

    def setup_models(self):
        # branch subarea
        create_area(
            x=0,
            y=0,
            width=10,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "101")],
        )
        # branch parent
        create_area(
            x=0,
            y=0,
            width=100,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "102")],
        )

    def csv_rows(self):
        return [
            {
                "area_type": "LBR",
                "area_id": "1",
                "area_gss": "LBR_1",
                "area_name": "branch name",
                "gss_code": "101",
                "parent_gss_code": "102",
            },
        ]


class WarnsAndDropsBranchIfParentDoesntOverlap(ShouldSucceed, Base):
    expected_creations = 0
    expected_areas_count = 2
    expected_warning_substring = "doesn't overlap with parent area"

    def setup_models(self):
        # branch subarea
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "101")],
        )
        # branch parent
        create_area(
            x=501,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "102")],
        )

    def csv_rows(self):
        return [
            {
                "area_type": "LBR",
                "area_id": "1",
                "area_gss": "LBR_1",
                "area_name": "branch name",
                "gss_code": "101",
                "parent_gss_code": "102",
            },
        ]


class WarnsIfExistingParentChanges(ShouldSucceed, Base):
    expected_creations = 0
    expected_updates = 1
    expected_areas_count = 4
    expected_warning_substring = "changed parent"

    def setup_models(self):
        # branch subarea
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "101")],
        )
        # branch parent
        p = create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "102")],
        )
        # branch
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=labour_branch_area_type(),
            codes=[(gss_code_type(), "LBR_1"), (labour_branch_code_type(), "1")],
            parent=p,
        )
        # new branch parent
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "103")],
        )

    def csv_rows(self):
        return [
            {
                "area_type": "LBR",
                "area_id": "1",
                "area_gss": "LBR_1",
                "area_name": "branch name",
                "gss_code": "101",
                "parent_gss_code": "103",
            },
        ]


class WarnsIfNoAreaFoundForParent(ShouldSucceed, Base):
    expected_creations = 1
    expected_areas_count = 2
    expected_warning_substring = "Parent area with GSS code '103' does not exist"

    def setup_models(self):
        # branch subarea
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "101")],
        )

    def csv_rows(self):
        return [
            {
                "area_type": "LBR",
                "area_id": "1",
                "area_gss": "LBR_1",
                "area_name": "branch name",
                "gss_code": "101",
                "parent_gss_code": "103",
            },
        ]


class WarnsIfNoAreaFoundForSubarea(ShouldSucceed, Base):
    expected_creations = 1
    expected_areas_count = 1
    expected_warning_substring = "Subarea with GSS code '102' doesn't exist."

    def setup_models(self):
        # branch subarea
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "101")],
        )
        # parent
        create_area(
            x=0,
            y=0,
            width=500,
            area_type=non_labour_area_type(),
            codes=[(gss_code_type(), "103")],
        )

    def csv_rows(self):
        return [
            {
                "area_type": "LBR",
                "area_id": "1",
                "area_gss": "LBR_1",
                "area_name": "branch name",
                "gss_code": "101",
                "parent_gss_code": "103",
            },
            {
                "area_type": "LBR",
                "area_id": "1",
                "area_gss": "LBR_1",
                "area_name": "branch name",
                "gss_code": "102",
                "parent_gss_code": "103",
            },
        ]


class RemovesOldAreasWhenPurgeIsTrue(ShouldSucceed, Base):
    purge = True
    expected_area_values_by_gss = {}
    expected_area_count = 0
    expected_created = 0
    expected_updated = 0

    def setup_models(self):
        # region area
        create_area(
            x=0,
            y=0,
            width=750,
            area_type=labour_region_area_type(),
            codes=[(gss_code_type(), "LR_1"), (labour_region_code_type(), "1")],
        )
