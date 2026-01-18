import logging
from typing import TYPE_CHECKING, Any

from src.core.config_loader import SectionConfig
from src.core.context_manager import SectionContext
from src.export.word_exporter import CHAPTER_STRUCTURE
from src.generators.base import BaseGenerator
from src.llm.client import LLMClient
from src.parsers.input_parser import ProjectInput

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
	from src.core.context_manager import ContextManager


class AutomatedSectionGenerator(BaseGenerator):
	def __init__(self, llm_client: LLMClient, config: dict[str, Any], context_manager: 'ContextManager'):
		super().__init__(llm_client, config, context_manager)

	def generate(
		self, section_config: SectionConfig, user_input: ProjectInput | None, context: dict[str, Any]
	) -> SectionContext:
		logger.info(f'Generating automated section: {section_config.name}')

		name_lower = section_config.name.lower()

		if 'definition' in name_lower and 'terms' in name_lower:
			content_raw = self._generate_definitions(user_input, context)

		elif 'organization' in name_lower:
			content_raw = self._generate_organization(context)

		elif 'requirement' in name_lower and 'system' in name_lower:
			content_raw = self._generate_system_requirements(user_input)

		elif 'hardware' in name_lower and 'requirement' in name_lower:
			content_raw = self._generate_hardware_requirements(user_input)

		elif 'software' in name_lower and 'requirement' in name_lower:
			content_raw = self._generate_software_requirements(user_input)

		elif 'user manual' in name_lower:
			content_raw = self._generate_user_manual(user_input)

		else:
			base_prompt = self._build_base_prompt(section_config, context)
			generic_prompt = f'Write the {section_config.name} section for this project.\n\n \
			After writing, extract 3-5 KEY POINTS in this format:\n\n---KEY_POINTS---\n- First key insight\n- \
			Second key insight\n...'
			content_raw = self.llm_client.generate(base_prompt + generic_prompt, temperature=0.5)

		content = self._remove_section_title_from_content(content_raw, section_config.name)
		content, key_points = self._parse_combined_response(content_raw)

		valid, word_count = self._validate_word_count(
			content, section_config.word_count['min'], section_config.word_count['max']
		)

		if not valid:
			content = self._adjust_content_length(
				content, section_config.word_count['min'], section_config.word_count['max'], section_config.name
			)
			word_count = self._count_words(content)
			_, key_points = self._parse_combined_response(content)

		citations = self._extract_citations(content)

		terms_defined = []
		if 'definition' in name_lower:
			terms_defined = self._extract_defined_terms(content)

		logger.info(f'Generated {word_count} words')

		return SectionContext(
			name=section_config.name,
			content=content,
			key_points=key_points,
			citations=citations,
			word_count=word_count,
			terms_defined=terms_defined,
		)

	def _generate_definitions(self, user_input: ProjectInput | None, context: dict[str, Any]) -> str:
		terms = set()

		if user_input:
			terms.update(user_input.extracted_terms or [])
			terms.update(user_input.keywords or [])

		all_terms_defined = context.get('all_terms_defined', [])
		terms.update(all_terms_defined)

		terms = list(terms)[:15]

		if not terms:
			terms = ['system', 'implementation', 'architecture', 'database']

		prompt = f"""Generate definitions for these technical terms. Define each term in 1-2 sentences in formal
			academic style.

	CRITICAL: Output ONLY the definitions in this exact format. No preamble, no "Here is...", no word counts.

	TERMS TO DEFINE:
	{', '.join(terms)}

	FORMAT:
	**Term 1**: Definition of term 1 in academic language.

	**Term 2**: Definition of term 2 in academic language.

	Write now:

	After writing, extract 3-5 KEY POINTS in this format:

	---KEY_POINTS---
	- First key insight
	- Second key insight
	..."""

		return self.llm_client.generate(prompt, temperature=0.5, max_tokens=1000)

	def _generate_organization(self, context: dict[str, Any]) -> str:
		num_chapters = len(CHAPTER_STRUCTURE)

		prompt = f"""Write the "Organization of the Study" section describing the paper structure.

	CRITICAL: Output ONLY the organization of study in this exact format. 
	No preamble, no "Here is...", no word counts.

	This paper is structured into {num_chapters} chapters:
	{chr(10).join([f'- {chapter}' for chapter in CHAPTER_STRUCTURE])}

	Describe what each chapter covers.

	Write now:

	After writing, extract 3-5 KEY POINTS in this format:

	---KEY_POINTS---
	- First key insight
	- Second key insight
	..."""

		return self.llm_client.generate(prompt, temperature=0.5, max_tokens=500)

	def _generate_system_requirements(self, user_input: ProjectInput | None) -> str:
		if not user_input:
			return 'System requirements were determined based on the implementation needs.'

		prompt = f"""Write a System Requirements section introducing both hardware and software requirements.

	PROJECT CONTEXT:
	Architecture: {user_input.system_architecture[:300]}
	Dependencies: {user_input.dependencies[:300]}

	Write a brief introduction to system requirements (hardware and software will be detailed separately).

	Write now:

	After writing, extract 3-5 KEY POINTS in this format:

	---KEY_POINTS---
	- First key insight
	- Second key insight
	..."""

		return self.llm_client.generate(prompt, temperature=0.5, max_tokens=400)

	def _generate_hardware_requirements(self, user_input: ProjectInput | None) -> str:
		if not user_input:
			return self._default_hardware_requirements()

		prompt = f"""List the hardware requirements for this system.

	PROJECT: {user_input.title}
	ARCHITECTURE: {user_input.system_architecture[:200]}

	Specify minimum hardware specifications (processor, RAM, storage, etc.) needed to run this system.
	Be specific and realistic.

	Write now:

	After writing, extract 3-5 KEY POINTS in this format:

	---KEY_POINTS---
	- First key insight
	- Second key insight
	..."""

		return self.llm_client.generate(prompt, temperature=0.5, max_tokens=400)

	def _generate_software_requirements(self, user_input: ProjectInput | None) -> str:
		if not user_input or not user_input.dependencies:
			return self._default_software_requirements()

		prompt = f"""List the software requirements for this system.

	DEPENDENCIES:
	{user_input.dependencies}

	List all software, frameworks, libraries, and tools needed. Include versions where relevant.
	Format as a clear list.

	Write now:

	After writing, extract 3-5 KEY POINTS in this format:

	---KEY_POINTS---
	- First key insight
	- Second key insight
	..."""

		return self.llm_client.generate(prompt, temperature=0.5, max_tokens=600)

	def _generate_user_manual(self, user_input: ProjectInput | None) -> str:
		if not user_input:
			return 'User manual covering system installation, configuration, and usage.'

		prompt = f"""Write a User Manual section for this system.

	SYSTEM: {user_input.title}
	SOLUTION: {user_input.solution[:400]}
	ARCHITECTURE: {user_input.system_architecture[:400]}

	Include:
	1. Installation instructions
	2. How to start/run the system
	3. Main features and how to use them
	4. Basic troubleshooting

	Be practical and step-by-step.

	Write now:

	After writing, extract 3-5 KEY POINTS in this format:

	---KEY_POINTS---
	- First key insight
	- Second key insight
	..."""

		return self.llm_client.generate(prompt, temperature=0.6, max_tokens=1500)

	def _default_hardware_requirements(self) -> str:
		return """The system requires standard computing hardware:

	- Processor: Intel Core i5 or equivalent (2.0 GHz minimum)
	- RAM: 4GB minimum, 8GB recommended
	- Storage: 10GB available disk space
	- Network: Stable internet connection
	- Display: 1024x768 resolution minimum"""

	def _default_software_requirements(self) -> str:
		return """The system requires the following software:

	- Operating System: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
	- Web Browser: Chrome 90+, Firefox 88+, or Safari 14+ (if web-based)
	- Runtime Environment: As specified by the implementation language
	- Database: As required by the architecture"""

	def _extract_defined_terms(self, content: str) -> list[str]:
		import re

		pattern = r'\*\*([^*]+)\*\*\s*[:–-]'
		terms = re.findall(pattern, content)

		return [t.strip() for t in terms if t.strip()]
