"""Public structured validation results.

Fatal problems raise an exception from `plugin_rosetta.errors`. Findings for
review are collected as `ValidationIssue` objects in a `ValidationReport`.
"""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict


class IssueSeverity(StrEnum):
    """Severity of a validation issue.

    Only `ERROR` makes a `ValidationReport` invalid.

    Attributes:
        ERROR: The input is unusable.
        WARNING: Should be fixed before publication.
        INFO: Informational; needs no action.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """One machine-readable validation issue.

    Attributes:
        code: Stable dotted identifier, for example `referential.unresolved`.
        severity: Seriousness of the issue.
        message: Human-readable explanation.
        location: Where the issue was found, if known. Mapping issues use
            `row 5, column subject_id`, where row 1 is the CSV header.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    severity: IssueSeverity
    message: str
    location: str | None = None


class ValidationReport(BaseModel):
    """Immutable collection of validation issues.

    Attributes:
        issues: The issues in the order in which they were found.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether no issue has severity `ERROR`."""
        return not any(issue.severity is IssueSeverity.ERROR for issue in self.issues)

    def merge(self, *others: Self) -> Self:
        """Return a new report with the issues of `others` appended.

        Args:
            *others: Reports to append, in order.
        """
        return type(self)(issues=self.issues + tuple(issue for report in others for issue in report.issues))
