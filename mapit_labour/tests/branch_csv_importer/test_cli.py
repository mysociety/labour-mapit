import re

from io import StringIO
from django.test import TestCase
from django.core.management import call_command, CommandError

from .skeletons import (
    ThrowsWhenGenerationDoesNotExist,
    ErrorsWhenCSVFileCantBeOpened,
    ErrorsWhenCSVIsMissingRequiredFields,
    ErrorsWhenUnknownAreaTypeGiven,
    ErrorsWhenRowIsMissingAreaId,
    ErrorsWhenRowIsMissingAreaName,
    ErrorsWhenRowIsMissingAreaGSS,
    ErrorsWhenRowIsMissingGSSCode,
    ErrorsWhenRowIsMissingParentGSSCode,
    ErrorsWhenRegionHasParent,
    ErrorsWhenBranchAreaIdsAreInconsistent,
    ErrorsWhenBranchParentGSSsAreInconsistent,
    ErrorsWhenBranchAreaNamesAreInconsistent,
    ErrorsWhenAreaAlreadyExistsForANonLabourEntity,
    SetsUpBranchesAndRegions,
    MakesNoChangesWhenCommitIsFalse,
    UsesTheCurrentGenerationWhenNoneIsGiven,
    SetsUpANewGenerationIfNewSpecified,
    UsesTheGivenGeneration,
    WarnsIfAreaIsSmall,
    WarnsAndDropsBranchIfParentDoesntOverlap,
    WarnsIfExistingParentChanges,
    WarnsIfNoAreaFoundForParent,
    WarnsIfNoAreaFoundForSubarea,
    RemovesOldAreasWhenPurgeIsTrue,
)


class Executor:
    def execute(
        self,
        commit,
        purge,
        csv_path,
        generation_id,
        generation_description,
    ):
        out_text = None
        try:
            with StringIO() as out:
                call_command(
                    "mapit_labour_import_branches",
                    csv_path,
                    commit=commit,
                    purge=purge,
                    stdout=out,
                )
                out_text = out.getvalue()
        except CommandError as e:
            return {"error": str(e)}

        created = int(re.findall(r"Created: (\d+)", out_text)[0])
        updated = int(re.findall(r"Updated: (\d+)", out_text)[0])
        warnings = re.findall(r"Warnings:.*\n(.*)", out_text)
        if warnings:
            warnings = warnings[0].split("\n")

        return {
            "error": None,
            "created": created,
            "updated": updated,
            "warnings": warnings if warnings else [],
        }


class ErrorsWhenCSVFileCantBeOpenedTest(
    Executor, ErrorsWhenCSVFileCantBeOpened, TestCase
):
    pass


class ErrorsWhenCSVIsMissingRequiredFieldsTest(
    Executor, ErrorsWhenCSVIsMissingRequiredFields, TestCase
):
    pass


class ErrorsWhenUnknownAreaTypeGivenTest(
    Executor, ErrorsWhenUnknownAreaTypeGiven, TestCase
):
    pass


class ErrorsWhenRowIsMissingAreaIdTest(
    Executor, ErrorsWhenRowIsMissingAreaId, TestCase
):
    pass


class ErrorsWhenRowIsMissingAreaNameTest(
    Executor, ErrorsWhenRowIsMissingAreaName, TestCase
):
    pass


class ErrorsWhenRowIsMissingAreaGSSTest(
    Executor, ErrorsWhenRowIsMissingAreaGSS, TestCase
):
    pass


class ErrorsWhenRowIsMissingGSSCodeTest(
    Executor, ErrorsWhenRowIsMissingGSSCode, TestCase
):
    pass


class ErrorsWhenRowIsMissingParentGSSCodeTest(
    Executor, ErrorsWhenRowIsMissingParentGSSCode, TestCase
):
    pass


class ErrorsWhenRegionHasParentTest(Executor, ErrorsWhenRegionHasParent, TestCase):
    pass


class ErrorsWhenBranchAreaIdsAreInconsistentTest(
    Executor, ErrorsWhenBranchAreaIdsAreInconsistent, TestCase
):
    pass


class ErrorsWhenBranchParentGSSsAreInconsistentTest(
    Executor, ErrorsWhenBranchParentGSSsAreInconsistent, TestCase
):
    pass


class ErrorsWhenBranchAreaNamesAreInconsistentTest(
    Executor, ErrorsWhenBranchAreaNamesAreInconsistent, TestCase
):
    pass


class ErrorsWhenAreaAlreadyExistsForANonLabourEntityTest(
    Executor, ErrorsWhenAreaAlreadyExistsForANonLabourEntity, TestCase
):
    pass


class SetsUpBranchesAndRegionsTest(Executor, SetsUpBranchesAndRegions, TestCase):
    pass


class MakesNoChangesWhenCommitIsFalseTest(
    Executor, MakesNoChangesWhenCommitIsFalse, TestCase
):
    pass


class WarnsIfAreaIsSmallTest(Executor, WarnsIfAreaIsSmall, TestCase):
    pass


class WarnsAndDropsBranchIfParentDoesntOverlapTest(
    Executor, WarnsAndDropsBranchIfParentDoesntOverlap, TestCase
):
    pass


class WarnsIfExistingParentChangesTest(
    Executor, WarnsIfExistingParentChanges, TestCase
):
    pass


class WarnsIfNoAreaFoundForParentTest(Executor, WarnsIfNoAreaFoundForParent, TestCase):
    pass


class WarnsIfNoAreaFoundForSubareaTest(
    Executor, WarnsIfNoAreaFoundForSubarea, TestCase
):
    pass


class RemovesOldAreasWhenPurgeIsTrueTest(
    Executor, RemovesOldAreasWhenPurgeIsTrue, TestCase
):
    pass
