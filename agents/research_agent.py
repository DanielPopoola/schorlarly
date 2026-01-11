import os
import time
from pathlib import Path
from typing import Any

from agents.arxiv_provider import ArxivProvider
from agents.perplexity_provider import PerplexityProvider
from agents.search_provider import SearchProvider
from models import SearchResult
from search import PaperDeduplicator
from utils.logger import logger


class ResearchAgent:
	def __init__(
		self,
		storage_dir: Path | str = 'state/sources',
		max_papers_per_section: int = 5,
		search_timeout_minutes: int = 5,
	):
		self.storage_dir = Path(storage_dir)
		self.storage_dir.mkdir(parents=True, exist_ok=True)

		self.max_papers = max_papers_per_section
		self.timeout_seconds = search_timeout_minutes * 60

		self.providers = self._initialize_providers()

		self.deduplicator = PaperDeduplicator()

		self.sources_db: dict[str, dict[str, Any]] = {}

	def _initialize_providers(self) -> list[SearchProvider]:
		providers = []

		perplexity_key = os.getenv('PERPLEXITY_API_KEY')
		if perplexity_key:
			try:
				provider = PerplexityProvider(perplexity_key)
				providers.append(provider)
			except Exception as e:
				logger.warning(f'Failed to initialize Perplexity: {e}')
		else:
			logger.info('Perplexity API key not found, using arXiv only')

		arxiv_provider = ArxivProvider(download_dir=self.storage_dir / 'pdfs')
		providers.append(arxiv_provider)

		return providers

	def research_section(
		self,
		topic: str,
		section_title: str,
		section_objective: str,
	) -> list[str]:
		logger.info(f'\n{"=" * 60}')
		logger.info(f'RESEARCHING: {section_title}')
		logger.info(f'{"=" * 60}')

		start_time = time.time()

		query = self._build_search_query(topic, section_title, section_objective)

		raw_results = []
		for provider in self.providers:
			logger.info(f'Trying {provider.get_name()}...')

			try:
				results = provider.search(query, max_results=self.max_papers)
				if results:
					raw_results = results
					break  # Stop if we got results
				else:
					logger.info(f'{provider.get_name()} returned no results')
			except Exception as e:
				logger.warning(f'{provider.get_name()} failed: {e}')
				continue

		if not raw_results:
			logger.error('All search providers failed!')
			return []

		elapsed = time.time() - start_time
		if elapsed > self.timeout_seconds:
			logger.warning(f'Search timeout reached ({elapsed:.1f}s)')
			return []

		unique_results = self.deduplicator.deduplicate(raw_results)
		logger.info(f'After deduplication: {len(unique_results)} unique papers')

		validated_sources = []
		for result in unique_results:
			if self._validate_source(result):
				validated_sources.append(result)

			elapsed = time.time() - start_time
			if elapsed > self.timeout_seconds:
				logger.warning(f'Validation timeout reached ({elapsed:.1f}s)')
				break

		logger.info(f'Validated {len(validated_sources)} sources')

		source_ids = []
		for source in validated_sources:
			source_id = self._store_source(source)
			source_ids.append(source_id)

		elapsed = time.time() - start_time
		logger.info(f'Research complete in {elapsed:.1f}s')
		logger.info(f'{"=" * 60}\n')

		return source_ids

	def _build_search_query(
		self,
		topic: str,
		section_title: str,
		section_objective: str,
	) -> str:
		query_parts = [topic]

		section_lower = section_title.lower()

		if 'methodology' in section_lower or 'method' in section_lower:
			query_parts.append('methods')
		elif 'literature' in section_lower or 'review' in section_lower:
			query_parts.append('survey review')

		query = ' '.join(query_parts)

		if len(query) > 200:
			query = query[:200]

		return query

	def _validate_source(self, result: SearchResult) -> bool:
		if not result.authors or len(result.authors) == 0:
			logger.debug(f'Rejected {result.source_id}: No authors')
			return False

		if not result.source_id.startswith('arxiv:'):
			logger.debug(f'Rejected {result.source_id}: Not an arXiv paper')
			return False

		if not result.content or len(result.content.strip()) < 50:
			logger.debug(f'Rejected {result.source_id}: No abstract')
			return False

		if not result.year:
			logger.debug(f'Rejected {result.source_id}: No publication year')
			return False

		if not result.url:
			logger.debug(f'Rejected {result.source_id}: No URL')
			return False

		return True

	def _store_source(self, result: SearchResult) -> str:
		source_id = result.source_id

		if source_id in self.sources_db:
			return source_id

		# Store metadata
		self.sources_db[source_id] = {
			'source_id': source_id,
			'title': result.title,
			'authors': result.authors,
			'year': result.year,
			'url': result.url,
			'abstract': result.content,
			'metadata': result.metadata,
			'validation_status': 'validated',
			'validation_reason': 'Passed all acceptance criteria',
		}

		logger.debug(f'Stored source: {source_id}')
		return source_id

	def get_source(self, source_id: str) -> dict[str, Any] | None:
		return self.sources_db.get(source_id)

	def get_all_sources(self) -> dict[str, dict[str, Any]]:
		return self.sources_db.copy()


# Example usage
if __name__ == '__main__':
	agent = ResearchAgent(
		storage_dir='state/sources',
		max_papers_per_section=3,
	)

	# Test research
	source_ids = agent.research_section(
		topic='microplastics marine biodiversity',
		section_title='Introduction',
		section_objective='Introduce the problem and establish context',
	)

	print(f'\nFound {len(source_ids)} sources:')
	for source_id in source_ids:
		source = agent.get_source(source_id)
		print(f'  - {source_id}: {source["title"][:60]}...')  # type: ignore
