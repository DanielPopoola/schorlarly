from dataclasses import dataclass
from .paper import SectionSummary

@dataclass
class GlobalState:
    thesis: str
    key_terms: dict[str, str]
    section_summaries: list[SectionSummary]
    decisions_made: list[str]
    current_section_id: int
    total_tokens_used : int
    retry_count: dict[int, int]