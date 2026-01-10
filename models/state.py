from dataclasses import dataclass, field

from .paper import SectionSummary


@dataclass
class GlobalState:
	thesis: str
	key_terms: dict[str, str] = field(default_factory=dict)  # {"term": "definition"}
	section_summaries: list[SectionSummary] = field(default_factory=list)
	decisions_made: list[str] = field(default_factory=list)
	current_section_id: int = 0
	total_tokens_used: int = 0
	cost_usd: float = 0.0
	retry_counts: dict[int, int] = field(default_factory=dict)  # {section_id: attempt_count}

	def record_retry(self, section_id: int) -> None:
		self.retry_counts[section_id] = self.retry_counts.get(section_id, 0) + 1

	def get_retry_count(self, section_id: int) -> int:
		return self.retry_counts.get(section_id, 0)

	def add_decision(self, decision: str) -> None:
		self.decisions_made.append(f'[Section {self.current_section_id}] {decision}')
