import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import arxiv
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class Paper:
	title: str
	authors: list[str]
	abstract: str
	year: int | None
	url: str
	source: str


class BaseSearcher(ABC):
	@abstractmethod
	def search(self, query: str, max_results: int = 10) -> list[Paper]:
		pass


class PerplexitySearcher(BaseSearcher):
	def __init__(self, api_key: str):
		self.api_key = api_key
		self.endpoint = 'https://api.perplexity.ai/chat/completions'

	@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
	def search(self, query: str, max_results: int = 10) -> list[Paper]:
		logger.info(f'Searching Perplexity for: {query}')

		prompt = f"""Find {max_results} academic papers about: {query}

For each paper, provide:
- Title
- Authors (comma-separated)
- Abstract (first 200 words)
- Year
- URL

Format as JSON array:
[{{"title": "...", "authors": ["..."], "abstract": "...", "year": 2023, "url": "..."}}]"""

		response = requests.post(
			self.endpoint,
			headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
			json={'model': 'llama-3.1-sonar-small-128k-online', 'messages': [{'role': 'user', 'content': prompt}]},
			timeout=30,
		)

		response.raise_for_status()
		content = response.json()['choices'][0]['message']['content']

		import json

		try:
			papers_data = json.loads(content)
			return [
				Paper(
					title=p['title'],
					authors=p.get('authors', []),
					abstract=p.get('abstract', ''),
					year=p.get('year'),
					url=p.get('url', ''),
					source='perplexity',
				)
				for p in papers_data[:max_results]
			]
		except (json.JSONDecodeError, KeyError) as e:
			logger.error(f'Failed to parse Perplexity response: {e}')
			return []


class ArXivSearcher(BaseSearcher):
	def search(self, query: str, max_results: int = 10) -> list[Paper]:
		logger.info(f'Searching arXiv for: {query}')

		client = arxiv.Client(delay_seconds=3, num_retries=3)
		search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)

		papers = []
		for result in client.results(search):
			papers.append(
				Paper(
					title=result.title,
					authors=[author.name for author in result.authors],
					abstract=result.summary,
					year=result.published.year if result.published else None,
					url=result.entry_id,
					source='arxiv',
				)
			)

		logger.info(f'Found {len(papers)} papers on arXiv')
		return papers


class ResearchSearcher:
	def __init__(self, config: dict[str, Any]):
		primary_config = config['primary']

		self.primary = (
			PerplexitySearcher(primary_config['api_key']) if primary_config['provider'] == 'perplexity' else None
		)
		self.fallback = ArXivSearcher()
		self.max_results = primary_config.get('max_results', 20)

	def search(self, query: str, max_results: int | None = None) -> list[Paper]:
		max_results = max_results or self.max_results
		papers = []

		if self.primary:
			try:
				papers = self.primary.search(query, max_results)
				if papers:
					logger.info(f'Got {len(papers)} papers from primary source')
			except Exception as e:
				logger.warning(f'Primary search failed: {e}')

		if len(papers) < max_results // 2:
			logger.info('Using fallback search')
			fallback_papers = self.fallback.search(query, max_results)
			papers.extend(fallback_papers)

		papers = self._deduplicate(papers)
		return papers[:max_results]

	def _deduplicate(self, papers: list[Paper]) -> list[Paper]:
		seen_titles = set()
		unique_papers = []

		for paper in papers:
			title_normalized = paper.title.lower().strip()
			if title_normalized not in seen_titles:
				seen_titles.add(title_normalized)
				unique_papers.append(paper)

		return unique_papers

	def build_search_query(self, domain: str, keywords: list[str], problem_statement: str) -> str:
		"""Build focused search query from project context"""
		# Extract key phrases from problem statement (first 50 words) to avoid overly long queries
		problem_snippet = ' '.join(problem_statement.split()[:50])

		# Combine domain + top keywords
		query_parts = [domain] + keywords[:7]

		# Add problem snippet if it exists
		if problem_snippet:
			query_parts.insert(0, problem_snippet)

		query = ' '.join(query_parts)

		# Ensure the total query length is not excessive for API limits
		max_query_length = 250  # A reasonable limit for many search APIs
		if len(query) > max_query_length:
			query = query[:max_query_length]
			# Try to end on a whole word if possible
			last_space = query.rfind(' ')
			if last_space > 0:
				query = query[:last_space]

		logger.info(f'Built search query: {query}')
		return query
