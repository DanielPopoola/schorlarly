from typing import Any

from src.generators.automated_section import AutomatedSectionGenerator
from src.generators.base import BaseGenerator
from src.generators.evidence_section import EvidenceSectionGenerator
from src.generators.interactive_section import InteractiveSectionGenerator
from src.generators.research_section import ResearchSectionGenerator
from src.generators.synthesis_section import SynthesisSectionGenerator
from src.llm.client import LLMClient
from src.research.searcher import ResearchSearcher
from src.research.validator import CitationValidator


class GeneratorFactory:
	def __init__(
		self,
		llm_client: LLMClient,
		config: dict[str, Any],
		research_searcher: ResearchSearcher,
		citation_validator: CitationValidator,
	):
		self.llm_client = llm_client
		self.config = config
		self.research_searcher = research_searcher
		self.citation_validator = citation_validator

		self._generators: dict[str, BaseGenerator] = {}

	def get_generator(self, section_type: str) -> BaseGenerator:
		if section_type in self._generators:
			return self._generators[section_type]

		if section_type == 'research':
			generator = ResearchSectionGenerator(
				self.llm_client, self.config, self.research_searcher, self.citation_validator
			)
		elif section_type == 'evidence':
			generator = EvidenceSectionGenerator(self.llm_client, self.config)
		elif section_type == 'interactive':
			generator = InteractiveSectionGenerator(self.llm_client, self.config)
		elif section_type == 'synthesis':
			generator = SynthesisSectionGenerator(self.llm_client, self.config)
		elif section_type == 'automated':
			generator = AutomatedSectionGenerator(self.llm_client, self.config)
		else:
			raise ValueError(f'Unknown section type: {section_type}')

		self._generators[section_type] = generator
		return generator


__all__ = [
	'GeneratorFactory',
	'BaseGenerator',
	'ResearchSectionGenerator',
	'EvidenceSectionGenerator',
	'InteractiveSectionGenerator',
	'SynthesisSectionGenerator',
	'AutomatedSectionGenerator',
]
