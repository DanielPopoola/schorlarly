from collections.abc import Sequence
from difflib import SequenceMatcher

from src.models import CitationReference, SearchResult
from src.utils.logger import logger


class PaperDeduplicator:
	def __init__(self, title_similarity_threshold: float = 0.85):
		self.title_similarity_threshold = title_similarity_threshold

	def deduplicate(self, results: Sequence[SearchResult]) -> list[SearchResult]:
		if not results:
			return []

		logger.info(f'Deduplicating {len(results)} search results...')

		merged_indices = set()
		unique_results: list[SearchResult] = []

		for i, result_a in enumerate(results):
			if i in merged_indices:
				continue

			duplicates = [result_a]

			for j, result_b in enumerate(results[i + 1 :], start=i + 1):
				if j in merged_indices:
					continue

				if self._are_duplicates(result_a, result_b):
					duplicates.append(result_b)
					merged_indices.add(j)

			merged = self._merge_results(duplicates)
			unique_results.append(merged)

		logger.info(
			f'Deduplication complete: {len(results)} → {len(unique_results)} '
			f'({len(results) - len(unique_results)} duplicates removed)'
		)

		return unique_results

	def _are_duplicates(self, a: SearchResult, b: SearchResult) -> bool:
		arxiv_id_a = self._extract_arxiv_id(a)
		arxiv_id_b = self._extract_arxiv_id(b)
		if arxiv_id_a and arxiv_id_b and arxiv_id_a == arxiv_id_b:
			logger.debug(f'Duplicate found (arXiv): {arxiv_id_a}')
			return True

		doi_a = self._extract_doi(a)
		doi_b = self._extract_doi(b)
		if doi_a and doi_b and doi_a == doi_b:
			logger.debug(f'Duplicate found (DOI): {doi_a}')
			return True

		if a.year and b.year and a.year == b.year:
			similarity = self._title_similarity(a.title, b.title)
			if similarity >= self.title_similarity_threshold:
				logger.debug(
					f'Duplicate found (title {similarity:.2f}): '
					f'{a.title[:40]}... = {b.title[:40]}...'
				)
				return True

		return False

	def _merge_results(self, duplicates: list[SearchResult]) -> SearchResult:
		if len(duplicates) == 1:
			return duplicates[0]

		sorted_dups = sorted(
			duplicates,
			key=lambda r: (
				bool(r.metadata.get('pdf_path')),
				len(r.content),
				len(r.citations),
			),
			reverse=True,
		)

		best = sorted_dups[0]

		all_citations: list[CitationReference] = []
		seen_identifiers = set()

		for result in sorted_dups:
			for citation in result.citations:
				if citation.identifier not in seen_identifiers:
					all_citations.append(citation)
					seen_identifiers.add(citation.identifier)

		merged_metadata = best.metadata.copy()
		merged_metadata['merged_from_sources'] = [r.source_id for r in duplicates]

		return SearchResult(
			source_id=best.source_id,
			title=best.title,
			content=best.content,
			authors=best.authors or self._merge_authors(duplicates),
			year=best.year or self._find_year(duplicates),
			url=best.url or self._find_url(duplicates),
			citations=all_citations,
			metadata=merged_metadata,
		)

	def _extract_arxiv_id(self, result: SearchResult) -> str | None:
		if result.source_id.startswith('arxiv:'):
			return result.source_id.split(':', 1)[1]

		return result.metadata.get('arxiv_id')

	def _extract_doi(self, result: SearchResult) -> str | None:
		doi = result.metadata.get('doi')
		if doi:
			return doi

		for citation in result.citations:
			if citation.identifier_type == 'doi':
				return citation.identifier

		return None

	def _title_similarity(self, title_a: str, title_b: str) -> float:
		a = ' '.join(title_a.lower().split())
		b = ' '.join(title_b.lower().split())

		return SequenceMatcher(None, a, b).ratio()

	def _merge_authors(self, results: list[SearchResult]) -> list[str] | None:
		all_authors = []
		for result in results:
			if result.authors:
				all_authors.extend(result.authors)

		seen = set()
		unique_authors = []
		for author in all_authors:
			if author.lower() not in seen:
				unique_authors.append(author)
				seen.add(author.lower())

		return unique_authors if unique_authors else None

	def _find_year(self, results: list[SearchResult]) -> int | None:
		for result in results:
			if result.year:
				return result.year
		return None

	def _find_url(self, results: list[SearchResult]) -> str | None:
		for result in results:
			if result.url:
				return result.url
		return None
