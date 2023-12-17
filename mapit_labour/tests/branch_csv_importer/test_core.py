from django.test import TestCase

from mapit_labour.importers import BranchCSVImporter

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
        return BranchCSVImporter.import_from_csv(
            path=csv_path,
            purge=purge,
            commit=commit,
            generation=generation_id,
            generation_description=generation_description,
        )


class ThrowsWhenGenerationDoesNotExistTest(
    Executor, ThrowsWhenGenerationDoesNotExist, TestCase
):
    pass


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


class UsesTheCurrentGenerationWhenNoneIsGivenTest(
    Executor, UsesTheCurrentGenerationWhenNoneIsGiven, TestCase
):
    pass


class SetsUpANewGenerationIfNewSpecifiedTest(
    Executor, SetsUpANewGenerationIfNewSpecified, TestCase
):
    pass


class UsesTheGivenGenerationTest(Executor, UsesTheGivenGeneration, TestCase):
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
