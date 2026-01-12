from dataclasses import dataclass
from enum import Enum


class SectionType(Enum):
	"""Different types of sections require different processing"""

	RESEARCH_LITERATURE = 'research_literature'  # Heavy citations
	TECHNICAL_ANALYSIS = 'technical_analysis'  # Diagrams, data
	IMPLEMENTATION = 'implementation'  # Code, demos
	METHODOLOGY = 'methodology'  # Procedures
	DISCUSSION = 'discussion'  # Analysis
	INTRO_CONCLUSION = 'intro_conclusion'  # Context, summary


@dataclass
class SectionProfile:
	"""Defines how to process a specific section"""

	section_type: SectionType
	min_citations: int
	min_word_count: int
	max_word_count: int
	requires_code: bool = False
	requires_diagrams: bool = False
	research_strategy: str = 'global'  # "global" or "targeted"


@dataclass
class TemplateProfile:
	"""Defines processing rules for an entire template"""

	name: str
	discipline: str
	default_citation_count: int
	sections: dict[str, SectionProfile]

	@classmethod
	def create_generic_academic(cls) -> 'TemplateProfile':
		"""Profile for general academic papers (your current system)"""
		return cls(
			name='generic_academic',
			discipline='general',
			default_citation_count=5,
			sections={
				'Introduction': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=3, min_word_count=800, max_word_count=1500
				),
				'Literature Review': SectionProfile(
					section_type=SectionType.RESEARCH_LITERATURE,
					min_citations=10,
					min_word_count=1500,
					max_word_count=2500,
					research_strategy='targeted',  # Needs deep literature search
				),
				'Research Methodology': SectionProfile(
					section_type=SectionType.METHODOLOGY, min_citations=5, min_word_count=1000, max_word_count=2000
				),
				'Key Findings': SectionProfile(
					section_type=SectionType.DISCUSSION, min_citations=7, min_word_count=1500, max_word_count=2500
				),
				'Discussion': SectionProfile(
					section_type=SectionType.DISCUSSION, min_citations=5, min_word_count=1000, max_word_count=2000
				),
				'Conclusion and Recommendations': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=2, min_word_count=600, max_word_count=1200
				),
			},
		)

	@classmethod
	def create_cs_project(cls) -> 'TemplateProfile':
		"""Profile for CS implementation projects"""
		return cls(
			name='cs_project',
			discipline='computer_science',
			default_citation_count=3,  # CS projects cite less
			sections={
				# CHAPTER ONE
				'Introduction': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=2, min_word_count=500, max_word_count=800
				),
				'Background to the Study': SectionProfile(
					section_type=SectionType.RESEARCH_LITERATURE,
					min_citations=5,
					min_word_count=800,
					max_word_count=1500,
				),
				'Statement of the Problem': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=2, min_word_count=400, max_word_count=800
				),
				'Objective of the Study': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=1, min_word_count=300, max_word_count=600
				),
				'Significance of the Study': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=2, min_word_count=400, max_word_count=800
				),
				'Scope of the Study': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=0, min_word_count=300, max_word_count=600
				),
				# CHAPTER TWO
				'Literature Review': SectionProfile(
					section_type=SectionType.RESEARCH_LITERATURE,
					min_citations=8,
					min_word_count=1500,
					max_word_count=2500,
					research_strategy='targeted',
				),
				'Existing Approaches to the Problem': SectionProfile(
					section_type=SectionType.RESEARCH_LITERATURE,
					min_citations=6,
					min_word_count=1000,
					max_word_count=2000,
				),
				"Researcher's Specific Approach": SectionProfile(
					section_type=SectionType.METHODOLOGY, min_citations=3, min_word_count=600, max_word_count=1200
				),
				# CHAPTER THREE
				'System Analysis': SectionProfile(
					section_type=SectionType.TECHNICAL_ANALYSIS,
					min_citations=3,
					min_word_count=800,
					max_word_count=1500,
					requires_diagrams=True,
				),
				'System Design': SectionProfile(
					section_type=SectionType.TECHNICAL_ANALYSIS,
					min_citations=2,
					min_word_count=1000,
					max_word_count=2000,
					requires_diagrams=True,
				),
				# CHAPTER FOUR
				'System Implementation': SectionProfile(
					section_type=SectionType.IMPLEMENTATION,
					min_citations=1,
					min_word_count=800,
					max_word_count=1500,
					requires_code=True,
				),
				'System Test-Run': SectionProfile(
					section_type=SectionType.IMPLEMENTATION,
					min_citations=0,
					min_word_count=600,
					max_word_count=1200,
					requires_code=True,
				),
				# CHAPTER FIVE
				'Summary': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=0, min_word_count=400, max_word_count=800
				),
				'Conclusion': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=1, min_word_count=400, max_word_count=800
				),
				'Recommendations': SectionProfile(
					section_type=SectionType.INTRO_CONCLUSION, min_citations=0, min_word_count=300, max_word_count=600
				),
			},
		)

	def get_section_profile(self, section_title: str) -> SectionProfile:
		"""Get profile for a section, with fuzzy matching"""
		# Exact match first
		if section_title in self.sections:
			return self.sections[section_title]

		# Fuzzy match (e.g., "1.1 Background to the Study" → "Background to the Study")
		section_lower = section_title.lower()
		for key, profile in self.sections.items():
			if key.lower() in section_lower or section_lower in key.lower():
				return profile

		# Default fallback
		return SectionProfile(
			section_type=SectionType.DISCUSSION,
			min_citations=self.default_citation_count,
			min_word_count=800,
			max_word_count=1500,
		)


class TemplateProfileManager:
	"""Manages template profiles and selection"""

	def __init__(self):
		self.profiles = {
			'generic_academic': TemplateProfile.create_generic_academic(),
			'cs_project': TemplateProfile.create_cs_project(),
		}

	def detect_profile(self, template: list[str], topic: str) -> TemplateProfile:
		"""Auto-detect which profile to use based on template structure"""
		template_lower = [s.lower() for s in template]

		# CS indicators
		cs_keywords = [
			'system implementation',
			'system design',
			'system analysis',
			'test-run',
			'program documentation',
			'user manual',
		]

		cs_score = sum(1 for keyword in cs_keywords if any(keyword in section for section in template_lower))

		if cs_score >= 3:  # Strong CS signal
			return self.profiles['cs_project']

		# Default to generic academic
		return self.profiles['generic_academic']

	def get_profile(self, name: str) -> TemplateProfile:
		"""Get profile by name"""
		return self.profiles.get(name, self.profiles['generic_academic'])
