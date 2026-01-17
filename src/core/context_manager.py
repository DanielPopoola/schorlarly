import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
	from src.research.searcher import Paper


@dataclass
class SectionContext:
	name: str
	content: str
	key_points: list[str]
	citations: list[str]
	word_count: int
	terms_defined: list[str] | None = None
	diagrams: list[dict] | None = None
	paper_references: list[dict] | None = None

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> 'SectionContext':
		if 'diagrams' not in data:
			data['diagrams'] = None
		if 'paper_references' not in data:
			data['paper_references'] = None
		return cls(**data)


class ContextManager:
	def __init__(self, state_file: Path | None = None):
		self.sections: dict[str, SectionContext] = {}
		self.all_citations: list[str] = []
		self.all_terms_defined: list[str] = []
		self.section_order: list[str] = []
		self.state_file = state_file
		self.citation_registry: dict[str, tuple[int, dict]] = {}  # key → (number, paper_dict)
		self.next_citation_num = 1

	def add_section(self, section_context: SectionContext):
		self.sections[section_context.name] = section_context
		self.section_order.append(section_context.name)

		self.all_citations.extend(section_context.citations)
		if section_context.terms_defined:
			self.all_terms_defined.extend(section_context.terms_defined)

		if self.state_file:
			self.save_state()

	def get_section(self, name: str) -> SectionContext | None:
		return self.sections.get(name)

	def get_context_for_section(self, section_name: str, dependencies: list[str]) -> dict[str, Any]:
		dependent_sections: dict[str, Any] = {}
		for dep_name in dependencies:
			if dep_name in self.sections:
				dependent_sections[dep_name] = {'name': dep_name}

		return {
			'section_name': section_name,
			'previously_completed': self.section_order.copy(),
			'dependent_sections': dependent_sections,
			'all_citations_used': self.all_citations.copy(),
			'all_terms_defined': self.all_terms_defined.copy(),
			'key_points_covered': self._get_all_key_points()[:30],
		}

	def _get_all_key_points(self) -> list[str]:
		all_points = []
		for section in self.sections.values():
			all_points.extend(section.key_points)
		return all_points

	def register_paper(self, paper: 'Paper') -> int:
		key = self._make_paper_key(paper)
		if key in self.citation_registry:
			return self.citation_registry[key][0]

		num = self.next_citation_num
		paper_dict = {
			'title': paper.title,
			'authors': paper.authors,
			'year': paper.year,
			'url': paper.url,
			'abstract': paper.abstract[:200],  # Truncate for storage
			'source': paper.source,
		}
		self.citation_registry[key] = (num, paper_dict)
		self.next_citation_num += 1

		return num

	def _make_paper_key(self, paper: 'Paper') -> str:
		title_clean = ''.join(c for c in paper.title.lower() if c.isalnum() or c.isspace())
		title_short = '_'.join(title_clean.split()[:5])
		return f'{title_short}_{paper.year or "unknown"}'

	def has_citation(self, citation: str) -> bool:
		return citation in self.all_citations

	def has_term(self, term: str) -> bool:
		return term.lower() in [t.lower() for t in self.all_terms_defined]

	def get_summary(self) -> dict[str, Any]:
		return {
			'total_sections': len(self.sections),
			'completed_sections': self.section_order,
			'total_words': sum(s.word_count for s in self.sections.values()),
			'total_citations': len(set(self.all_citations)),
			'sections_by_content': {
				name: {'key_points': section.key_points, 'word_count': section.word_count}
				for name, section in self.sections.items()
			},
		}

	def save_state(self):
		if not self.state_file:
			return

		state = {
			'sections': {name: section.to_dict() for name, section in self.sections.items()},
			'section_order': self.section_order,
			'all_citations': self.all_citations,
			'all_terms_defined': self.all_terms_defined,
			'citation_registry': {
				key: {'number': num, 'paper': paper_dict} for key, (num, paper_dict) in self.citation_registry.items()
			},
			'next_citation_num': self.next_citation_num,
		}

		self.state_file.parent.mkdir(parents=True, exist_ok=True)
		with open(self.state_file, 'w') as f:
			json.dump(state, f, indent=2)

	def load_state(self):
		if not self.state_file or not self.state_file.exists():
			return

		with open(self.state_file) as f:
			state = json.load(f)

		self.sections = {name: SectionContext.from_dict(data) for name, data in state['sections'].items()}
		self.section_order = state['section_order']
		self.all_citations = state['all_citations']
		self.all_terms_defined = state['all_terms_defined']
		if 'citation_registry' in state:
			self.citation_registry = {
				key: (data['number'], data['paper']) for key, data in state['citation_registry'].items()
			}
			self.next_citation_num = state.get('next_citation_num', 1)

	def clear(self):
		self.sections.clear()
		self.all_citations.clear()
		self.all_terms_defined.clear()
		self.section_order.clear()

		if self.state_file and self.state_file.exists():
			self.state_file.unlink()
