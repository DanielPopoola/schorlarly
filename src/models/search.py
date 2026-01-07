from dataclasses import dataclass
from typing import Any


@dataclass
class SearchResult:
    source_id: str
    title: str
    content: str
    authors: list[str] | None
    year: int | None
    url: str | None
    citations: list[str]
    metadata: dict[str, Any]
