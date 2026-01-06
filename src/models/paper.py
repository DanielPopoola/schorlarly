from enum import Enum
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    text: str
    source_ids: list[str]
    section_id: int


@dataclass(frozen=True)
class SectionSummary:
    section_id: int
    section_title: str
    summary: str
    key_findings: list[Finding]
    key_terms: list[str]


class EvidenceType(Enum):
    EMPIRICAL_FINDING = "empirical_finding"
    STATISTICAL_RESULT = "statistical_result"
    THEORETICAL_CLAIM = "theoretical_claim"
    METHODOLOGICAL = "methodological"
    BACKGROUND = "background"


@dataclass(frozen=True)
class Claim:
    claim_id: str
    source_id: str
    statement: str
    context: str | None
    evidence_type: EvidenceType
    tags: list[str]
    page_number: int | None
    section_in_source: str | None
    confidence: float = 1.0
    extracted_at: str | None = None


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
