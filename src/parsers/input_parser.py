import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.llm.client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class ProjectInput:
	title: str
	author: str
	domain: str
	keywords: list[str]
	problem_statement: str
	solution: str
	approach_justification: str
	system_architecture: str
	dependencies: str
	implementation_highlights: str = ''
	test_results: str = ''

	# Additional context
	raw_content: str = ''
	extracted_terms: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)


class InputParser:
	def __init__(self, llm_client: LLMClient | None = None):
		self.llm_client = llm_client

	def parse_file(self, file_path: Path) -> ProjectInput:
		logger.info(f'Parsing input file: {file_path}')

		with open(file_path) as f:
			content = f.read()

		return self.parse_content(content)

	def parse_content(self, content: str) -> ProjectInput:
		sections = self._extract_sections(content)

		metadata = self._extract_metadata(sections.get('Project Configuration', ''))

		# Build ProjectInput
		project_input = ProjectInput(
			title=metadata.get('title', 'Untitled Project'),
			author=metadata.get('author', 'Anonymous'),
			domain=metadata.get('domain', 'General'),
			keywords=metadata.get('keywords', []),
			problem_statement=sections.get('Problem Statement', ''),
			solution=sections.get('Your Solution', ''),
			approach_justification=sections.get('Why This Approach', ''),
			system_architecture=sections.get('System Architecture', ''),
			dependencies=sections.get('Dependencies', ''),
			implementation_highlights=sections.get('Implementation Highlights', ''),
			test_results=sections.get('Test Results', ''),
			raw_content=content,
		)

		if self.llm_client:
			project_input.extracted_terms = self._extract_terms_with_llm(project_input)

		logger.info(f'Parsed project: {project_input.title}')
		logger.info(f'  Domain: {project_input.domain}')
		logger.info(f'  Keywords: {", ".join(project_input.keywords)}')

		return project_input

	def _extract_sections(self, content: str) -> dict[str, str]:
		sections = {}
		current_section = None
		current_content = []

		for line in content.split('\n'):
			if line.startswith('# '):
				if current_section:
					sections[current_section] = '\n'.join(current_content).strip()

				current_section = line[2:].strip()
				current_content = []
			else:
				if current_section:
					current_content.append(line)

		if current_section:
			sections[current_section] = '\n'.join(current_content).strip()

		return sections

	def _extract_metadata(self, config_section: str) -> dict[str, Any]:
		metadata = {}

		for line in config_section.split('\n'):
			if ':' in line:
				key, value = line.split(':', 1)
				key = key.strip().lower()
				value = value.strip()

				if key == 'keywords':
					metadata[key] = [k.strip() for k in value.split(',')]
				else:
					metadata[key] = value

		return metadata

	def _extract_terms_with_llm(self, project_input: ProjectInput) -> list[str]:
		prompt = f"""Extract technical terms from this project description that would need 
		definition in an academic paper.

PROJECT TITLE: {project_input.title}

DOMAIN: {project_input.domain}

PROBLEM: {project_input.problem_statement[:500]}

SOLUTION: {project_input.solution[:500]}

ARCHITECTURE: {project_input.system_architecture[:500]}

Extract 5-10 technical terms that are:
1. Domain-specific (not common words)
2. Important to understanding the project
3. Would benefit from definition in the paper

Return ONLY a comma-separated list of terms, nothing else.
Example: microservices, API gateway, load balancing, containerization"""

		try:
			response = self.llm_client.generate(prompt, temperature=0.3, max_tokens=200)

			terms = [term.strip() for term in response.split(',')]
			logger.info(f'Extracted {len(terms)} technical terms')
			return terms

		except Exception as e:
			logger.warning(f'Failed to extract terms with LLM: {e}')
			return []

	def get_context_for_section(self, project_input: ProjectInput, section_type: str) -> str:
		context_map = {
			'research': f"""
DOMAIN: {project_input.domain}
KEYWORDS: {', '.join(project_input.keywords)}
PROBLEM: {project_input.problem_statement}
""",
			'interactive': f"""
PROBLEM: {project_input.problem_statement}
SOLUTION: {project_input.solution}
JUSTIFICATION: {project_input.approach_justification}
""",
			'evidence': f"""
ARCHITECTURE: {project_input.system_architecture}
IMPLEMENTATION: {project_input.implementation_highlights}
TEST RESULTS: {project_input.test_results}
DEPENDENCIES: {project_input.dependencies}
""",
			'automated': f"""
TITLE: {project_input.title}
DOMAIN: {project_input.domain}
ARCHITECTURE: {project_input.system_architecture}
DEPENDENCIES: {project_input.dependencies}
TERMS: {', '.join(project_input.extracted_terms)}
""",
		}

		return context_map.get(section_type, project_input.raw_content[:1000])
