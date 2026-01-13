import re
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
		project_type: str,
		artifacts: list[dict],
		guidance: str,
		available_sources: list[dict[str, Any]],
		style_preferences: dict[str, Any],
		constraints: dict[str, Any],
		previous_section_text: str | None = None,
		avoid_repetition: bool = False,
	) -> dict[str, Any]:
		logger.info(f'\n{"=" * 60}')
		logger.info(f'WRITING: {section_title}')
		logger.info(f'{"=" * 60}')

		start_time = time.time()

		prompt = self._build_writing_prompt(
			section_title=section_title,
			section_objective=section_objective,
			topic=topic,
			project_type=project_type,
			artifacts=artifacts,
			guidance=guidance,
			available_sources=available_sources,
			style_preferences=style_preferences,
			constraints=constraints,
			previous_section_text=previous_section_text,
		)

		try:
			content = self._generate_content(prompt, constraints)
			content = self._adjust_claims_for_project_type(content, project_type)
		except Exception as e:
			logger.error(f'Content generation failed: {e}')
			raise

		word_count = self._count_words(content)
		citations_used = self._extract_citations(content)
		content = self._validate_citations_post_write(content, available_sources)

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

	def _adjust_claims_for_project_type(self, content: str, project_type: str) -> str:
		"""Downgrade false claims based on project type for proposals."""
		if project_type == 'proposal':
			replacements = {
				'we conducted': 'we will conduct',
				'we collected': 'we will collect',
				'we analyzed': 'we will analyze',
				'results show': 'expected results will show',
				'we found': 'we expect to find',
				'our experiment': 'our proposed experiment',
				'this study demonstrated': 'this proposed study will demonstrate',
				'the system performs': 'the proposed system will perform',
				'we implemented': 'we will implement',
			}

			for old, new in replacements.items():
				# Use regex for whole word matching to avoid partial replacements
				content = re.sub(r'\b' + re.escape(old) + r'\b', new, content, flags=re.IGNORECASE)

			logger.info(f'  Claims adjusted for {project_type} project type.')

		return content

	def _build_writing_prompt(
		self,
		section_title: str,
		section_objective: str,
		topic: str,
		project_type: str,
		artifacts: list[dict],
		guidance: str,
		available_sources: list[dict[str, Any]],
		style_preferences: dict[str, Any],
		constraints: dict[str, Any],
		previous_section_text: str | None,
		avoid_repetition: bool = False,
	) -> str:
		sources_text = '# AVAILABLE SOURCES (CITE USING EXACT IDs)\n\n'

		for source in available_sources:
			sources_text += f"""
			**Source ID: {source['source_id']}** ← USE THIS EXACT ID IN CITATIONS
			Title: {source['title']}
			Authors: {', '.join(source['authors'])}
			Year: {source['year']}
			Abstract: {source['abstract'][:300]}...

			"""

		artifacts_text = ''
		if artifacts:
			artifacts_text = '# PROJECT ARTIFACTS (YOUR ORIGINAL WORK)\n'
			for a in artifacts:
				artifacts_text += f'- {a["type"]}: {a["description"]}\n'
		else:
			artifacts_text = '# NO ORIGINAL ARTIFACTS PROVIDED\n'

		epistemic_constraints = ''
		if project_type == 'review':
			epistemic_constraints = """
# CRITICAL EPISTEMIC CONSTRAINTS (PROJECT TYPE: REVIEW)
1. You are writing a SYSTEMATIC REVIEW.
2. DO NOT claim to have performed any original experiments, measurements, or software development.
3. FORBIDDEN phrases: "I measured", "We developed", "Our system", "In our study".
4. REQUIRED phrases: "The literature indicates", "Previous studies by [Source] suggest", 
"A synthesis of existing work reveals".
5. If a claim isn't in the provided SOURCES, you cannot state it as a primary finding of this paper.
"""
		elif project_type == 'proposal':
			epistemic_constraints = """
# CRITICAL EPISTEMIC CONSTRAINTS (PROJECT TYPE: PROPOSAL)
1. You are writing a RESEARCH PROPOSAL for future work.
2. Use FUTURE TENSE for all methodology and expected results ("We will measure", 
"The proposed system will").
3. DO NOT claim that results have already been obtained.
"""
		elif project_type in ['empirical', 'computational']:
			if not artifacts:
				epistemic_constraints = f"""
# CRITICAL EPISTEMIC CONSTRAINTS (PROJECT TYPE: {project_type.upper()} BUT NO ARTIFACTS)
1. WARNING: This project is categorized as {project_type}, but no original artifacts were provided.
2. YOU MUST DOWNGRADE your claims. Instead of reporting results, focus on "Proposed Methodology"
 or "Theoretical Framework".
3. DO NOT hallucinate specific data points or code features that haven't been provided in the 
ARTIFACTS section.
4. If you must discuss results, label them as "EXPECTED OUTCOMES" or "SIMULATED SCENARIOS".
"""
			else:
				epistemic_constraints = f"""
# CRITICAL EPISTEMIC CONSTRAINTS (PROJECT TYPE: {project_type.upper()})
1. You may report findings based ONLY on the provided ARTIFACTS.
2. Be precise about what YOU did vs what the SOURCES report.
"""

		style_text = self._format_style_instructions(style_preferences)

		target_words = constraints.get('max_section_word_count', 1500)
		min_citations = constraints.get('min_citations_per_section', 3)

		if avoid_repetition and previous_section_text:
			context_instruction = f"""
		# CONTENT FROM PREVIOUS SECTION (DO NOT REPEAT)

		{previous_section_text[:500]}...

		# CRITICAL INSTRUCTION

		The previous section already covered:
		- Background concepts
		- General definitions
		- Problem context

		DO NOT re-explain these. Instead:
		- Assume the reader already knows the basics
		- Focus ONLY on the specific objective of THIS section
		- Build upon (don't repeat) what was said before
		- Use phrases like "As discussed previously" instead of re-explaining

		If you find yourself defining terms like "RAG" or "Knowledge Graph" again, STOP.
		Those were already defined in earlier sections.
		"""
		else:
			context_instruction = ''

		example_source_id = available_sources[0]['source_id'] if available_sources else 'arxiv:1234.5678'

		example_citations = f"""
# CITATION EXAMPLES (COPY THIS FORMAT EXACTLY)

✅ CORRECT:
"Graph neural networks improve retrieval [{example_source_id}]."
"The authors found that [{example_source_id}: \\"accuracy increased by 15%\\"]."

❌ WRONG (DO NOT USE):
"Recent work [source_id] shows..." ← Generic placeholder
"Studies [1] demonstrate..." ← Numbered reference
"According to research [arxiv] or [arxiv:XXXXX]..." ← Bare "arxiv" or made-up ID
"""

		prompt = f"""You are an expert academic writer.

# PAPER CONTEXT
Topic: {topic}
Project Type: {project_type}
Section: {section_title}
Objective: {section_objective}

# GLOBAL GUIDANCE FOR THIS SECTION
{guidance}

{epistemic_constraints}

{artifacts_text}

# YOUR TASK
Write {target_words} words (±20% acceptable) with at least {min_citations} citations.

{context_instruction}

{sources_text}

{example_citations}

# CRITICAL CITATION RULES

1. ONLY use source IDs from the list above (e.g., {example_source_id})
2. NEVER use placeholders like [source_id], [source_01], [1], [2]
3. EVERY factual claim needs a citation with a real ID
4. If you can't find a relevant source, rephrase the claim more generally

# STYLE
{style_text}

# CRITICAL HYGIENE
- NEVER mention that you are an AI or that this was "Generated by Scholarly".
- DO NOT include internal metadata or future timestamps.

# OUTPUT FORMAT
Write in Markdown. Begin now:"""

		return prompt

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

	def _validate_citations_post_write(self, content: str, available_sources: list) -> str:
		"""Check for placeholder citations and warn"""
		import re

		# Find all citations
		citations = re.findall(r'\[([^\]]+)\]', content)

		placeholder_patterns = [
			r'^source_?\d*$',  # [source_id], [source01]
			r'^\d+$',  # [1], [2]
			r'^ref_?\d*$',  # [ref_01]
			r'^citation$',  # [citation]
			r'^arxiv$',  # [arxiv]
		]

		valid_ids = {s['source_id'] for s in available_sources}

		warnings = []
		for citation in citations:
			citation_clean = citation.strip()

			# 1. Check if it's a valid ID (or starts with one, to handle [ID: "quote"])
			is_valid = False
			if citation_clean in valid_ids:
				is_valid = True
			else:
				for vid in valid_ids:
					if citation_clean.startswith(f'{vid}:'):
						is_valid = True
						break

			if is_valid:
				continue

			# 2. Check if it's a placeholder
			is_placeholder = any(re.match(pattern, citation_clean, re.IGNORECASE) for pattern in placeholder_patterns)

			if is_placeholder:
				warnings.append(f'Found placeholder citation: [{citation}]')
				# Remove placeholder from content
				content = content.replace(f'[{citation}]', '')
			else:
				warnings.append(f'Invalid citation (not in sources): [{citation_clean}]')

		if warnings:
			logger.warning('Citation issues found:\n' + '\n'.join(warnings))

		return content
