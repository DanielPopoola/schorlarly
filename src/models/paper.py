"""
Paper models define the structure of the output document being generated.
"""

from enum import Enum
from dataclasses import dataclass


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
    extracted_at: str | None = None  # ISO timestamp


class SectionStatus(Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    FAILED = "failed"


@dataclass(frozen=True)
class Citation:
    claim_id: str
    quoted_text: str
    location_in_section: int


@dataclass
class Section:
    section_id: int
    title: str
    content: str
    citations: list[Citation]
    word_count: int
    status: SectionStatus = SectionStatus.DRAFT
    created_at: str | None = None  # ISO timestamp


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
