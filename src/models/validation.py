from enum import Enum
from dataclasses import dataclass


class IssueType(Enum):
    CITATION_MISSING = "citation_missing"
    CITATION_INVALID = "citation_invalid"
    CITATION_QUOTE_MISMATCH = "citation_quote_mismatch"
    WORD_COUNT = "word_count"
    QUESTION_NOT_ANSWERED = "question_not_answered"
    STYLE_MISMATCH = "style_mismatch"
    TERMINOLOGY_INCONSISTENT = "terminology_inconsistent"


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationIssue:
    issue_type: IssueType
    severity: Severity
    message: str
    suggestion: str | None
    location: str | None


@dataclass(frozen=True)
class ValidationResult:
    validation_id: str
    section_id: int
    passed: bool
    issues: list[ValidationIssue]
    attempt: int
    timestamp: str
