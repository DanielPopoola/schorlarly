import time
from typing import Any

from utils.logger import logger


class WritingAgent:
	def __init__(
		self,
		llm_client: Any,  # Will be UnifiedLLMClient from your codebase
		max_generation_time_minutes: int = 10,
	):
		self.llm_client = llm_client
		self.timeout_seconds = max_generation_time_minutes * 60

	def write_section(
		self,
		section_title: str,
		section_objective: str,
		topic: str,
		available_sources: list[dict[str, Any]],
		style_preferences: dict[str, Any],
		constraints: dict[str, Any],
		previous_section_text: str | None = None,
	) -> dict[str, Any]:
		logger.info(f'\n{"=" * 60}')
		logger.info(f'WRITING: {section_title}')
		logger.info(f'{"=" * 60}')

		start_time = time.time()

		prompt = self._build_writing_prompt(
			section_title=section_title,
			section_objective=section_objective,
			topic=topic,
			available_sources=available_sources,
			style_preferences=style_preferences,
			constraints=constraints,
			previous_section_text=previous_section_text,
		)

		try:
			content = self._generate_content(prompt, constraints)
		except Exception as e:
			logger.error(f'Content generation failed: {e}')
			raise

		word_count = self._count_words(content)
		citations_used = self._extract_citations(content)

		elapsed = time.time() - start_time

		logger.info(f'✓ Generated {word_count} words')
		logger.info(f'✓ Used {len(citations_used)} citations')
		logger.info(f'✓ Completed in {elapsed:.1f}s')
		logger.info(f'{"=" * 60}\n')

		return {
			'content': content,
			'word_count': word_count,
			'citations_used': citations_used,
			'generation_time': elapsed,
		}

	def _build_writing_prompt(
		self,
		section_title: str,
		section_objective: str,
		topic: str,
		available_sources: list[dict[str, Any]],
		style_preferences: dict[str, Any],
		constraints: dict[str, Any],
		previous_section_text: str | None,
	) -> str:
		sources_text = self._format_sources_for_prompt(available_sources)

		style_text = self._format_style_instructions(style_preferences)

		target_words = constraints.get('max_section_word_count', 1500)
		min_citations = constraints.get('min_citations_per_section', 3)

		context_text = ''
		if previous_section_text:
			context_text = f"""
## PREVIOUS SECTION (For Continuity)

{previous_section_text[:500]}...

Ensure this section flows naturally from the previous one.
"""

		prompt = f"""You are an academic writer helping to write a research paper.

# PAPER TOPIC
{topic}

# CURRENT SECTION
Title: {section_title}
Objective: {section_objective}

# YOUR TASK
Write the "{section_title}" section of the paper. This section should:
- {section_objective}
- Be approximately {target_words} words
- Include at least {min_citations} citations
- Be well-structured with clear paragraphs
- Use academic tone and formal language

{context_text}

# STYLE REQUIREMENTS
{style_text}

# AVAILABLE SOURCES (You MUST cite from these)

{sources_text}

# CITATION FORMAT (CRITICAL - READ CAREFULLY)

You MUST use this exact citation format:

**For general references:**
[source_id]

Example: "Transformers revolutionized NLP [arxiv:2301.12345]."

**For direct quotes or specific claims:**
[source_id: "quoted text"]

Example: "The attention mechanism [arxiv:2301.12345: "allows models to weigh input tokens"] 
improves context."

**RULES:**
1. ONLY cite sources from the "AVAILABLE SOURCES" list above
2. Every factual claim must have a citation
3. Use source_id exactly as shown (e.g., arxiv:2301.12345)
4. For direct quotes, use the [source_id: "quote"] format
5. DO NOT invent or hallucinate citations
6. DO NOT cite sources not in the list

# OUTPUT FORMAT

Write the section in Markdown format:
- Use ## for subsection headings (if needed)
- Use proper paragraphs
- Include citations inline
- Do not include the section title (it will be added automatically)

Begin writing now:"""

		return prompt

	def _format_sources_for_prompt(self, sources: list[dict[str, Any]]) -> str:
		if not sources:
			return 'No sources available (this section should rely on general knowledge)'

		formatted = []
		for i, source in enumerate(sources, 1):
			source_id = source.get('source_id', 'unknown')
			title = source.get('title', 'Unknown Title')
			authors = source.get('authors', [])
			year = source.get('year', 'Unknown')
			abstract = source.get('abstract', '')

			authors_str = ', '.join(authors[:3]) if authors else 'Unknown'
			if len(authors) > 3:
				authors_str += ' et al.'

			abstract_short = abstract[:300] + '...' if len(abstract) > 300 else abstract

			formatted.append(f"""
[{i}] **{source_id}**
Title: {title}
Authors: {authors_str}
Year: {year}
Abstract: {abstract_short}
""")

		return '\n'.join(formatted)

	def _format_style_instructions(self, style: dict[str, Any]) -> str:
		tone = style.get('tone', 'professional')
		complexity = style.get('complexity', 'undergraduate')
		citation_format = style.get('citation_format', 'APA')
		additional = style.get('additional_instructions', '')

		instructions = f"""
- Tone: {tone}
- Complexity level: {complexity}
- Citation style: {citation_format}
"""

		if additional:
			instructions += f'- Additional requirements: {additional}\n'

		return instructions

	def _generate_content(self, prompt: str, constraints: dict) -> str:
		target_words = constraints.get('max_section_word_count', 1500)
		max_tokens = int(target_words * 1.5)
		content = self.llm_client.generate(prompt, max_tokens=max_tokens)
		return content.strip()

	def _count_words(self, text: str) -> int:
		words = text.split()
		return len(words)

	def _extract_citations(self, text: str) -> list[str]:
		import re

		pattern = r'\[(arxiv:\S+?|doi:\S+?)(?::\s*"[^"]*")?\]'
		matches = re.findall(pattern, text)
		return list(set(matches))
