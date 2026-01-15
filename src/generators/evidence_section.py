import logging
from typing import Any

from src.core.config_loader import SectionConfig
from src.core.context_manager import SectionContext
from src.generators.base import BaseGenerator
from src.parsers.input_parser import ProjectInput

logger = logging.getLogger(__name__)


class EvidenceSectionGenerator(BaseGenerator):
	def generate(
		self, section_config: SectionConfig, user_input: ProjectInput | None, context: dict[str, Any]
	) -> SectionContext:
		logger.info(f'Generating evidence section: {section_config.name}')

		if not user_input:
			raise ValueError('Evidence sections require user input')

		# Extract relevant evidence based on section type
		evidence = self._extract_evidence(section_config.name, user_input)

		# Handle code-required sections
		code_snippet = None
		if section_config.code_required:
			code_snippet = self._handle_code_section(section_config.name, user_input)

		# Build prompt
		base_prompt = self._build_base_prompt(section_config, context)
		evidence_prompt = self._build_evidence_prompt(section_config, evidence, code_snippet)

		full_prompt = base_prompt + evidence_prompt

		# Generate
		content = self.llm_client.generate(
			full_prompt, temperature=0.6, max_tokens=section_config.word_count['max'] * 2
		)

		# Adjust word count if needed
		valid, word_count = self._validate_word_count(
			content, section_config.word_count['min'], section_config.word_count['max']
		)

		if not valid:
			content = self._adjust_content_length(
				content, section_config.word_count['min'], section_config.word_count['max'], section_config.name
			)
			word_count = self._count_words(content)

		# Extract metadata
		key_points = self._extract_key_points(content)
		citations = self._extract_citations(content)

		logger.info(f'Generated {word_count} words with {len(key_points)} key points')

		return SectionContext(
			name=section_config.name,
			content=content,
			key_points=key_points,
			citations=citations,
			word_count=word_count,
			terms_defined=[],
		)

	def _extract_evidence(self, section_name: str, user_input: ProjectInput) -> str:
		"""Extract relevant data from user input based on section type"""
		name_lower = section_name.lower()

		if 'system analysis' in name_lower:
			return f"""PROBLEM: {user_input.problem_statement}

SOLUTION: {user_input.solution}

ARCHITECTURE: {user_input.system_architecture}"""

		elif 'system design' in name_lower or 'architecture' in name_lower:
			return f"""ARCHITECTURE:
{user_input.system_architecture}

APPROACH JUSTIFICATION:
{user_input.approach_justification}

DEPENDENCIES:
{user_input.dependencies}"""

		elif 'implementation' in name_lower:
			return f"""ARCHITECTURE:
{user_input.system_architecture}

IMPLEMENTATION HIGHLIGHTS:
{user_input.implementation_highlights}

DEPENDENCIES:
{user_input.dependencies}"""

		elif 'test' in name_lower:
			return f"""TEST RESULTS:
{user_input.test_results}

IMPLEMENTATION CONTEXT:
{user_input.implementation_highlights}"""

		elif 'flowchart' in name_lower or 'menu' in name_lower:
			return f"""SYSTEM ARCHITECTURE:
{user_input.system_architecture}

SOLUTION OVERVIEW:
{user_input.solution}"""

		elif 'documentation' in name_lower:
			return f"""IMPLEMENTATION:
{user_input.implementation_highlights}

ARCHITECTURE:
{user_input.system_architecture}"""

		else:
			# Default: provide general context
			return f"""SOLUTION: {user_input.solution}
ARCHITECTURE: {user_input.system_architecture}
IMPLEMENTATION: {user_input.implementation_highlights}"""

	def _handle_code_section(self, section_name: str, user_input: ProjectInput) -> str | None:
		"""For code-required sections, use implementation highlights or prompt user"""
		if user_input.implementation_highlights:
			return user_input.implementation_highlights

		# If no code provided, prompt user
		logger.warning(f'{section_name} requires code but none provided in input')
		print(f'\n⚠️  Section "{section_name}" requires code examples.')
		print('Please provide implementation details in your input file.')
		return None

	def _build_evidence_prompt(self, section_config: SectionConfig, evidence: str, code_snippet: str | None) -> str:
		"""Build section-specific prompt with evidence"""
		name_lower = section_config.name.lower()

		if 'system analysis' in name_lower:
			prompt = f"""Write a System Analysis section that:
- Analyzes the current system/problem state
- Identifies inefficiencies and bottlenecks
- Justifies the need for a new solution
- References the problem statement

EVIDENCE:
{evidence}

Write in formal academic tone. Focus on analytical insights, not just description."""

		elif 'system design' in name_lower:
			prompt = f"""Write a System Design section that:
- Describes the overall architecture
- Explains component interactions
- Justifies design decisions
- Uses technical diagrams descriptions where helpful

DESIGN DETAILS:
{evidence}

Explain both WHAT the system does and WHY you designed it this way."""

		elif 'implementation' in name_lower:
			code_context = f'\n\nIMPLEMENTATION CODE/DETAILS:\n{code_snippet}' if code_snippet else ''

			prompt = f"""Write a System Implementation section that:
- Describes the actual implementation
- Explains key algorithms and logic
- Discusses interesting technical solutions
- References specific technologies used

IMPLEMENTATION EVIDENCE:
{evidence}{code_context}

Be technical but clear. Explain complex parts in detail."""

		elif 'test' in name_lower:
			prompt = f"""Write a Test-Run section that:
- Presents test methodology
- Shows actual test results (use tables if provided)
- Analyzes the results
- Discusses performance metrics

TEST DATA:
{evidence}

Present data clearly. Use tables for numeric results. Analyze what the results mean."""

		elif 'flowchart' in name_lower:
			prompt = f"""Write a section describing the system flowchart:
- Explain the overall process flow
- Describe key decision points
- Show how data moves through the system
- Reference architectural components

SYSTEM CONTEXT:
{evidence}

Describe the flow step-by-step. Make it easy to visualize."""

		elif 'documentation' in name_lower:
			prompt = f"""Write a Program Documentation section that:
- Documents the codebase structure
- Explains major modules/components
- Describes key functions and their purposes
- Provides usage examples

IMPLEMENTATION:
{evidence}

Focus on helping future developers understand the code."""

		else:
			prompt = f"""Write the {section_config.name} section using this evidence:

{evidence}

Maintain academic formal tone."""

		return prompt
