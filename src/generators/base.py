import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from src.core.config_loader import SectionConfig
from src.core.context_manager import SectionContext
from src.llm.client import LLMClient
from src.parsers.input_parser import ProjectInput

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
	def __init__(self, llm_client: LLMClient, config: dict[str, Any]):
		self.llm_client = llm_client
		self.writing_config = config.get('writing', {})
		self.citation_config = config.get('citation', {})

	@abstractmethod
	def generate(
		self, section_config: SectionConfig, user_input: ProjectInput | None, context: dict[str, Any]
	) -> SectionContext:
		raise NotImplementedError

	def _build_base_prompt(self, section_config: SectionConfig, context: dict[str, Any]) -> str:
		tone = self.writing_config.get('tone', 'formal-academic')
		citation_style = self.citation_config.get('style', 'IEEE')
		min_words = section_config.word_count['min']
		max_words = section_config.word_count['max']

		covered = context.get('key_points_covered', [])
		covered_str = '\n- '.join(covered[:10]) if covered else 'None yet'

		prompt = f"""You are writing an academic {section_config.name} section.

REQUIREMENTS:
- Writing tone: {tone}
- Citation style: {citation_style}
- Word count: {min_words}-{max_words} words
- Use third person, avoid "I/we"

ALREADY COVERED (do NOT repeat these):
- {covered_str}

"""
		return prompt

	def _extract_key_points(self, content: str) -> list[str]:
		prompt = f"""Extract 3-5 key points from this text. Return ONLY a numbered list, no preamble.

TEXT:
{content[:1500]}

FORMAT:
1. First key point
2. Second key point
..."""

		try:
			response = self.llm_client.generate(prompt, temperature=0.3, max_tokens=200)
			points = re.findall(r'\d+\.\s+(.+)', response)
			return [p.strip() for p in points if p.strip()]
		except Exception as e:
			logger.warning(f'Failed to extract key points: {e}')
			paragraphs = content.split('\n\n')
			return [p.split('.')[0] for p in paragraphs[:5] if p.strip()]

	def _extract_key_points_local(self, content: str) -> list[str]:
		# Try paragraph-based extraction first
		paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]

		if len(paragraphs) < 3:  # Not enough clear paragraphs
			# Fallback: split by sentences
			sentences = re.split(r'[.!?]+\s+', content)
			paragraphs = [s.strip() for s in sentences if len(s.split()) > 10]

		key_points = []

		for para in paragraphs[:7]:
			first_sentence = para.split('.')[0]
			if len(first_sentence.split()) > 5:
				key_points.append(first_sentence.strip())

		if len(key_points) < 3:
			result_sentences = [s for s in paragraphs if re.search(r'\d+%|\d+\.\d+|achieved|demonstrated|showed', s)]
			key_points.extend([s.split('.')[0] for s in result_sentences[:3]])

		return key_points[:5] if key_points else ['Content generated successfully']

	def _parse_combined_response(self, content: str) -> tuple[str, list[str]]:
		"""Parse content and key points from a combined LLM response."""
		if '---KEY_POINTS---' in content:
			parts = content.split('---KEY_POINTS---')
			actual_content = parts[0].strip()
			key_points_text = parts[1].strip()
			key_points = [
				line.strip('- ').strip() for line in key_points_text.split('\n') if line.strip().startswith('-')
			]
			return actual_content, key_points

		return content, self._extract_key_points_local(content)

	def _extract_citations(self, content: str) -> list[str]:
		ieee_pattern = r'\[\d+\]'
		apa_pattern = r'\([A-Z][a-z]+,?\s+\d{4}\)'

		citations = set()
		citations.update(re.findall(ieee_pattern, content))
		citations.update(re.findall(apa_pattern, content))

		return list(citations)

	def _count_words(self, text: str) -> int:
		return len(text.split())

	def _validate_word_count(self, content: str, min_words: int, max_words: int) -> tuple[bool, int]:
		count = self._count_words(content)
		valid = min_words <= count <= max_words
		return valid, count

	def _adjust_content_length(self, content: str, target_min: int, target_max: int, section_name: str) -> str:
		current_count = self._count_words(content)

		if current_count < target_min:
			adjustment_prompt = f"""Expand this {section_name} section to {target_min}-{target_max} words.
Add more detail and explanation while maintaining academic tone.

CURRENT TEXT ({current_count} words):
{content}

EXPANDED VERSION:"""
		else:  # Too long
			adjustment_prompt = f"""Condense this {section_name} section to {target_min}-{target_max} words.
Keep the most important points, remove redundancy.

CURRENT TEXT ({current_count} words):
{content}

CONDENSED VERSION:"""

		try:
			adjusted = self.llm_client.generate(adjustment_prompt, temperature=0.5, max_tokens=target_max * 2)
			return adjusted
		except Exception as e:
			logger.warning(f'Failed to adjust content length: {e}')
			return content
