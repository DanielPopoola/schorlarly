import logging
import re
from dataclasses import dataclass
from typing import Any

import requests

from src.llm.client import LLMClient
from src.research.searcher import Paper

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
	exists: bool
	relevance_score: float
	status: str
	reason: str


class CitationValidator:
	def __init__(self, llm_client: LLMClient, config: dict[str, Any]):
		self.llm_client = llm_client
		self.min_relevance = config['validation']['min_relevance_score']
		self.auto_accept = config['validation']['auto_accept_score']
		self.cache: dict[str, ValidationResult] = {}

	def validate(self, paper: Paper, domain_keywords: list[str]) -> ValidationResult:
		cache_key = paper.url or paper.title

		if cache_key in self.cache:
			logger.debug(f'Using cached validation for: {paper.title}')
			return self.cache[cache_key]

		exists = self._validate_existence(paper)
		if not exists:
			result = ValidationResult(exists=False, relevance_score=0.0, status='rejected', reason='Paper not found')
			self.cache[cache_key] = result
			return result

		relevance = self._validate_relevance(paper, domain_keywords)

		if relevance >= self.auto_accept:
			status = 'accepted'
			reason = f'High relevance ({relevance:.2f})'
		elif relevance >= self.min_relevance:
			status = 'flagged'
			reason = f'Moderate relevance ({relevance:.2f}) - review recommended'
		else:
			status = 'rejected'
			reason = f'Low relevance ({relevance:.2f})'

		result = ValidationResult(exists=True, relevance_score=relevance, status=status, reason=reason)
		self.cache[cache_key] = result

		logger.info(f'Validated "{paper.title[:50]}...": {status} ({relevance:.2f})')
		return result

	def _validate_existence(self, paper: Paper) -> bool:
		url = paper.url

		if 'arxiv.org' in url.lower():
			return True

		if 'doi.org' in url:
			try:
				response = requests.head(url, timeout=5, allow_redirects=True)
				return response.status_code == 200
			except requests.RequestException as e:
				logger.debug(f'DOI check failed for {url}: {e}')
				return False

		if url.startswith('http'):
			try:
				response = requests.head(url, timeout=5, allow_redirects=True, stream=True)
				response.close()
				return response.status_code == 200
			except requests.RequestException as e:
				logger.debug(f'URL check failed for {url}: {e}')
				return False

		return bool(paper.title and paper.abstract)

	def _validate_relevance(self, paper: Paper, domain_keywords: list[str]) -> float:
		keywords_str = ', '.join(domain_keywords)

		prompt = f"""Rate the relevance of this paper to the domain "{keywords_str}".

Paper Title: {paper.title}
Abstract: {paper.abstract[:500]}

Respond with ONLY a number between 0 and 1:
- 0.0 = completely irrelevant
- 0.5 = somewhat relevant
- 1.0 = highly relevant

Just output the number, nothing else."""

		try:
			response = self.llm_client.generate(prompt, temperature=0.1, max_tokens=10)
			score_str = response.strip()

			score_match = re.search(r'0?\.\d+|[01]\.?\d*', score_str)
			if score_match:
				score = float(score_match.group())
				return max(0.0, min(1.0, score))  # Clamp to [0, 1]

			logger.warning(f'Could not parse relevance score: {response}')
			return 0.5
		except Exception as e:
			logger.error(f'Relevance validation failed: {e}')
			return 0.5

	def validate_batch(self, papers: list[Paper], domain_keywords: list[str]) -> dict[str, ValidationResult]:
		results = {}

		for paper in papers:
			key = paper.url or paper.title
			results[key] = self.validate(paper, domain_keywords)

		# Log summary
		accepted = sum(1 for r in results.values() if r.status == 'accepted')
		flagged = sum(1 for r in results.values() if r.status == 'flagged')
		rejected = sum(1 for r in results.values() if r.status == 'rejected')

		logger.info(f'Batch validation: {accepted} accepted, {flagged} flagged, {rejected} rejected')

		return results
