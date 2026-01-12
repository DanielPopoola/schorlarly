import re
from datetime import datetime
from typing import Any

from models import IssueType, Severity, ValidationIssue, ValidationResult


class CitationValidator:
	def __init__(self, sources_db: dict[str, dict[str, Any]]):
		self.sources_db = sources_db
		self.citation_pattern = r'\[(arxiv:\S+?|doi:\S+?)(?::\s*"[^"]*")?\]'

	def validate_section(
		self, section_id: int, content: str, min_citations: int = 3, max_words: int = 2000
	) -> ValidationResult:
		issues = []

		# Extract all citations
		citations = re.findall(self.citation_pattern, content)
		unique_citations = set(citations)

		# Check each citation exists
		missing_sources = []
		for citation in unique_citations:
			if citation not in self.sources_db:
				issues.append(
					ValidationIssue(
						issue_type=IssueType.CITATION_INVALID,
						severity=Severity.CRITICAL,
						message=f'Citation {citation} not found in sources',
						suggestion='Remove citation or add source to database',
						location=None,
					)
				)
				missing_sources.append(citation)

		# Extract topics from missing citations for gap detection
		missing_topics = self._extract_topics_from_context(content, missing_sources)

		# Check minimum citations
		if len(unique_citations) < min_citations:
			issues.append(
				ValidationIssue(
					issue_type=IssueType.CITATION_MISSING,
					severity=Severity.WARNING,
					message=f'Only {len(unique_citations)} citations, need {min_citations}',
					suggestion=f'Add {min_citations - len(unique_citations)} more citations',
					location=None,
				)
			)

		# Check word count
		word_count = len(content.split())
		if abs(word_count - max_words) > max_words * 0.1:
			issues.append(
				ValidationIssue(
					issue_type=IssueType.WORD_COUNT,
					severity=Severity.WARNING,
					message=f'Word count {word_count} outside ±10% of {max_words}',
					suggestion=f'Adjust length to ~{max_words} words',
					location=None,
				)
			)

		return ValidationResult(
			validation_id=f'val_{section_id}_{datetime.now().isoformat()}',
			section_id=section_id,
			passed=len([i for i in issues if i.severity == Severity.CRITICAL]) == 0,
			issues=issues,
			attempt=1,
			timestamp=datetime.now().isoformat(),
			missing_topics=missing_topics if missing_sources else [],
		)

	def _extract_topics_from_context(self, content: str, missing_citations: list[str]) -> list[str]:
		"""Extract key terms around missing citations to identify research gaps"""
		topics = []
		for citation in missing_citations:
			# Find sentences containing the citation
			pattern = rf'[^.!?]*\{re.escape(citation)}[^.!?]*[.!?]'
			matches = re.findall(pattern, content)
			for match in matches:
				# Extract noun phrases (simplified)
				words = match.lower().split()
				# Filter for likely topic words (length > 4, not common words)
				keywords = [w for w in words if len(w) > 4 and w not in {'which', 'their', 'about'}]
				topics.extend(keywords[:3])  # Take first 3 keywords per sentence
		return list(set(topics))[:5]  # Return top 5 unique topics
