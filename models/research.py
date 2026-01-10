from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CitationReference:
	identifier: str
	identifier_type: str
	metadata: dict[str, Any] | None = None


@dataclass
class SearchResult:
	source_id: str
	title: str
	content: str
	authors: list[str] | None
	year: int | None
	url: str | None
	citations: list[CitationReference]
	metadata: dict[str, Any]


@dataclass(frozen=True)
class Question:
	question_id: str
	text: str
	target_sections: list[int]


@dataclass(frozen=True)
class ResearchPlan:
	topic: str
	questions: list[Question]
	total_sources: int
	completed_at: str  # ISO timestamp
