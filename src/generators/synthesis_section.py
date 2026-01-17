import logging
from typing import TYPE_CHECKING, Any

from src.core.config_loader import SectionConfig
from src.core.context_manager import SectionContext
from src.generators.base import BaseGenerator
from src.llm.client import LLMClient
from src.parsers.input_parser import ProjectInput

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
	from src.core.context_manager import ContextManager


class SynthesisSectionGenerator(BaseGenerator):
	def __init__(self, llm_client: LLMClient, config: dict[str, Any], context_manager: 'ContextManager'):
		super().__init__(llm_client, config, context_manager)

	def generate(
		self, section_config: SectionConfig, user_input: ProjectInput | None, context: dict[str, Any]
	) -> SectionContext:
		logger.info(f'Generating synthesis section: {section_config.name}')

		all_key_points = context.get('key_points_covered', [])
		completed_sections = context.get('previously_completed', [])

		section_summaries = self._get_section_summaries(context)

		base_prompt = self._build_base_prompt(section_config, context)
		synthesis_prompt = self._build_synthesis_prompt(
			section_config, all_key_points, completed_sections, section_summaries
		)

		full_prompt = base_prompt + synthesis_prompt

		content = self.llm_client.generate(
			full_prompt, temperature=0.6, max_tokens=section_config.word_count['max'] * 2
		)

		valid, word_count = self._validate_word_count(
			content, section_config.word_count['min'], section_config.word_count['max']
		)

		if not valid:
			content = self._adjust_content_length(
				content, section_config.word_count['min'], section_config.word_count['max'], section_config.name
			)
			word_count = self._count_words(content)

		key_points = self._extract_key_points_local(content)
		citations = self._extract_citations(content)

		logger.info(f'Generated {word_count} words summarizing {len(completed_sections)} sections')

		return SectionContext(
			name=section_config.name,
			content=content,
			key_points=key_points,
			citations=citations,
			word_count=word_count,
			terms_defined=[],
		)

	def _get_section_summaries(self, context: dict[str, Any]) -> dict[str, list[str]]:
		dependent_sections = context.get('dependent_sections', {})

		summaries = {}
		for section_name, section_data in dependent_sections.items():
			summaries[section_name] = section_data.get('key_points', [])

		return summaries

	def _build_synthesis_prompt(
		self,
		section_config: SectionConfig,
		all_key_points: list[str],
		completed_sections: list[str],
		section_summaries: dict[str, list[str]],
	) -> str:
		name_lower = section_config.name.lower()

		sections_list = '\n- '.join(completed_sections)
		points_summary = '\n\n'.join(
			[f'{section}:\n  - ' + '\n  - '.join(points) for section, points in section_summaries.items()]
		)

		if 'summary' in name_lower:
			prompt = f"""Write a comprehensive Summary of the entire paper.

SECTIONS COVERED:
- {sections_list}

KEY POINTS FROM EACH SECTION:
{points_summary}

Your Summary should:
- Recap the problem and why it matters
- Summarize the approach taken
- Highlight key findings/implementation
- Mention test results and outcomes
- Synthesize the main contributions

DO NOT introduce new information. Only synthesize what's already in the paper.
Make it comprehensive yet concise."""

		elif 'conclusion' in name_lower:
			prompt = f"""Write a Conclusion based on the entire paper.

PAPER SECTIONS:
- {sections_list}

KEY ACHIEVEMENTS:
{all_key_points}

Your Conclusion should:
- Restate the problem briefly
- Summarize what was accomplished
- Reflect on the significance
- Discuss how objectives were met
- Provide final thoughts on the work

Be definitive and confident. This is the final word on the project."""

		elif 'recommendation' in name_lower:
			prompt = f"""Write Recommendations for future work.

CURRENT WORK SUMMARY:
{all_key_points}

SECTIONS COMPLETED:
- {sections_list}

Your Recommendations should:
- Suggest improvements to the current system
- Propose future extensions or features
- Identify areas for further research
- Discuss scalability or deployment considerations
- Consider real-world implementation challenges

Be practical and forward-looking. What should happen next?"""

		else:
			# Generic synthesis
			prompt = f"""Synthesize the following information into a cohesive {section_config.name} section:

{points_summary}

Draw connections and provide a unified perspective."""

		return prompt
