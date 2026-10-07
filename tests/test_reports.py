from plugin_rosetta import IssueSeverity, ValidationIssue, ValidationReport


def test_report_without_issues_is_valid() -> None:
    assert ValidationReport().is_valid


def test_report_exposes_all_issues_and_is_invalid() -> None:
    issues = (
        ValidationIssue(
            code="mapping.required",
            severity=IssueSeverity.ERROR,
            location="row 2",
            message="subject_id is required",
        ),
        ValidationIssue(
            code="mapping.empty",
            severity=IssueSeverity.WARNING,
            location="row 3",
            message="reviewer_id is empty",
        ),
    )

    report = ValidationReport(issues=issues)

    assert not report.is_valid
    assert report.issues == issues


def test_report_merge_preserves_issue_order() -> None:
    first = ValidationReport(
        issues=(
            ValidationIssue(
                code="first",
                severity=IssueSeverity.WARNING,
                message="first issue",
            ),
        ),
    )
    second = ValidationReport(
        issues=(
            ValidationIssue(
                code="second",
                severity=IssueSeverity.ERROR,
                message="second issue",
            ),
        ),
    )

    merged = first.merge(second)

    assert [issue.code for issue in merged.issues] == ["first", "second"]
