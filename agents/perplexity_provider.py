import json
import re
from typing import Any

import requests

from agents.search_provider import SearchProvider
from models import SearchResult
from utils.logger import logger


class PerplexityProvider(SearchProvider):
	def __init__(self, api_key: str, model: str = 'sonar'):
		self.api_key = api_key
		self.model = model
		self.base_url = 'https://api.perplexity.ai/chat/completions'

	def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
		logger.info(f'Searching Perplexity for: {query}')

		prompt = self._build_search_prompt(query, max_results)

		try:
			response = self._call_api(prompt)
			papers = self._parse_response(response)
			logger.info(f'Perplexity found {len(papers)} papers')
			return papers
		except Exception as e:
			logger.error(f'Perplexity search failed: {e}')
			return []

	def get_name(self) -> str:
		return 'Perplexity'

	def supports_semantic_search(self) -> bool:
		return True

	def _build_search_prompt(self, query: str, max_results: int) -> str:
		return f"""Find the {max_results} most relevant and highly-cited academic papers about: {query}

For each paper, provide:
1. Title
2. Authors (all authors, comma-separated)
3. Year
4. arXiv ID or DOI (must be verifiable)
5. Brief summary (1-2 sentences)

Focus on:
- Foundational/seminal papers in this area
- Recent papers (2020-2024) with novel contributions
- Papers from reputable venues (top conferences, journals)

Format each paper as:
---
Title: [exact title]
Authors: [author1, author2, ...]
Year: [YYYY]
ID: [arxiv:XXXX.XXXXX or doi:XX.XXXX/XXXXX]
Summary: [1-2 sentences]
---

Only include papers you can verify exist. Do not hallucinate citations."""

	def _call_api(self, prompt: str) -> dict[str, Any]:
		headers = {
			'Authorization': f'Bearer {self.api_key}',
			'Content-Type': 'application/json',
		}

		payload = {
			'model': self.model,
			'messages': [
				{
					'role': 'system',
					'content': 'You are an academic research assistant helping find relevant papers. \
                    Only cite papers you can verify exist.',
				},
				{
					'role': 'user',
					'content': prompt,
				},
			],
		}

		response = requests.post(
			self.base_url,
			headers=headers,
			json=payload,
			timeout=30,
		)

		response.raise_for_status()
		return response.json()

	def _parse_response(self, response: dict[str, Any]) -> list[SearchResult]:
		try:
			content = response['choices'][0]['message']['content']

			papers = self._parse_papers_from_text(content)

			results = []
			for paper in papers:
				result = self._paper_to_search_result(paper)
				if result:
					results.append(result)

			return results

		except Exception as e:
			logger.error(f'Failed to parse Perplexity response: {e}')
			logger.debug(f'Response was: {json.dumps(response, indent=2)[:500]}')
			return []

	def _parse_papers_from_text(self, text: str) -> list[dict[str, str]]:
		papers = []

		sections = text.split('---')

		for section in sections:
			section = section.strip()
			if not section:
				continue

			paper = {}

			title_match = re.search(r'Title:\s*(.+)', section, re.IGNORECASE)
			if title_match:
				paper['title'] = title_match.group(1).strip()

			authors_match = re.search(r'Authors:\s*(.+)', section, re.IGNORECASE)
			if authors_match:
				authors_str = authors_match.group(1).strip()
				paper['authors'] = [a.strip() for a in authors_str.split(',')]

			year_match = re.search(r'Year:\s*(\d{4})', section, re.IGNORECASE)
			if year_match:
				paper['year'] = int(year_match.group(1))

			id_match = re.search(r'ID:\s*(arxiv:\S+|doi:\S+)', section, re.IGNORECASE)
			if id_match:
				paper['id'] = id_match.group(1).strip()

			summary_match = re.search(r'Summary:\s*(.+)', section, re.IGNORECASE | re.DOTALL)
			if summary_match:
				paper['summary'] = summary_match.group(1).strip()

			if 'title' in paper and 'id' in paper:
				papers.append(paper)

		return papers

	def _paper_to_search_result(self, paper: dict[str, str]) -> SearchResult | None:
		try:
			paper_id = paper.get('id', '')

			if paper_id.startswith('arxiv:'):
				source_id = paper_id
				url = f'https://arxiv.org/abs/{paper_id.replace("arxiv:", "")}'
			elif paper_id.startswith('doi:'):
				source_id = paper_id
				url = f'https://doi.org/{paper_id.replace("doi:", "")}'
			else:
				logger.warning(f'Unknown ID format: {paper_id}')
				return None

			return SearchResult(
				source_id=source_id,
				title=paper.get('title', 'Unknown'),
				content=paper.get('summary', ''),
				authors=paper.get('authors'),  # type: ignore
				year=paper.get('year'),  # type: ignore
				url=url,
				citations=[],  # Perplexity doesn't provide citation graph
				metadata={
					'provider': 'perplexity',
					'raw_id': paper_id,
				},
			)

		except Exception as e:
			logger.error(f'Failed to convert paper to SearchResult: {e}')
			return None
