from typing import Any

from models import Finding, SectionSummary


class ContextManager:
	def __init__(self, llm_client: Any):
		self.llm_client = llm_client
		self.summaries: list[SectionSummary] = []

	def summarize_section(
		self, section_id: int, section_title: str, content: str, sources_used: list[str]
	) -> SectionSummary:
		"""Compress a section into a concise summary with key findings"""

		prompt = f"""Summarize this academic paper section in 2-3 sentences.
Then extract 3-5 key findings with their source citations.

# Section: {section_title}

{content[:2000]}  # Truncate for LLM input

Output format:
SUMMARY: [2-3 sentence summary]

FINDINGS:
1. [Finding 1] (sources: arxiv:XXX, arxiv:YYY)
2. [Finding 2] (sources: arxiv:ZZZ)
..."""

		response = self.llm_client.generate(prompt, max_tokens=500)

		# Parse response
		lines = response.strip().split('\n')
		summary_text = ''
		findings = []

		in_findings = False
		for line in lines:
			if line.startswith('SUMMARY:'):
				summary_text = line.replace('SUMMARY:', '').strip()
			elif line.startswith('FINDINGS:'):
				in_findings = True
			elif in_findings and line.strip() and '(sources:' in line:
				text = line.split('(sources:')[0].strip().lstrip('0123456789. ')
				source_str = line.split('(sources:')[1].rstrip(')')
				source_ids = [s.strip() for s in source_str.split(',')]
				findings.append(Finding(text=text, source_ids=source_ids, section_id=section_id))

		# Extract key terms (simple: most common non-stopwords)
		words = content.lower().split()
		key_terms = self._extract_key_terms(words)

		summary = SectionSummary(
			section_id=section_id,
			section_title=section_title,
			summary=summary_text,
			key_findings=findings[:5],  # Limit to 5
			key_terms=key_terms[:10],  # Limit to 10
		)

		self.summaries.append(summary)
		return summary

	def get_context_for_section(self, current_section_id: int, window_size: int = 3) -> str:
		"""Get compressed context from prior sections"""
		if current_section_id == 0:
			return ''

		# Get last N summaries
		relevant_summaries = self.summaries[max(0, current_section_id - window_size) : current_section_id]

		context_parts = []
		for summary in relevant_summaries:
			context_parts.append(f"""
## {summary.section_title} (Summary)
{summary.summary}

Key findings:
{chr(10).join(f'- {f.text}' for f in summary.key_findings)}
""")

		return '\n'.join(context_parts)

	def extract_findings_for_refinement(self, section_id: int) -> list[Finding]:
		for summary in self.summaries:
			if summary.section_id == section_id:
				return summary.key_findings
		return []

	def _extract_key_terms(self, words: list[str]) -> list[str]:
		from collections import Counter

		stopwords = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'was', 'were'}
		meaningful = [w for w in words if len(w) > 4 and w not in stopwords]

		counter = Counter(meaningful)
		return [term for term, count in counter.most_common(10)]
