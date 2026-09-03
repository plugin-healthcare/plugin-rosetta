"""Structured validation results."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict


class IssueSeverity(StrEnum):
    """Severity of a validation issue."""

    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(BaseModel):
    """One machine-readable validation issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    severity: IssueSeverity
    message: str
    location: str | None = None


class ValidationReport(BaseModel):
    """Immutable collection of validation issues."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether no error was reported."""
        return not any(issue.severity is IssueSeverity.ERROR for issue in self.issues)

    def merge(self, *others: Self) -> Self:
        """Combine reports while preserving issue order."""
        return type(self)(issues=self.issues + tuple(issue for report in others for issue in report.issues))
