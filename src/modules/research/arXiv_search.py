from pathlib import Path

import arxiv

from src.models import CitationReference, SearchResult
from src.utils.logger import logger


class ArxivSearch:
	def __init__(self, download_dir: Path | str | None = None):
		self.download_dir = Path(download_dir) if download_dir else None
		if self.download_dir:
			self.download_dir.mkdir(parents=True, exist_ok=True)
			logger.info(f'arXiv PDFs will be saved to: {self.download_dir}')

	def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
		logger.info(f"Searching arXiv for: '{query}' (max {max_results} results)")

		client = arxiv.Client()
		search = arxiv.Search(
			query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
		)

		results: list[SearchResult] = []

		for idx, paper in enumerate(client.results(search), 1):
			logger.debug(f'  [{idx}/{max_results}] {paper.title[:60]}...')

			arxiv_id = paper.entry_id.split('/')[-1].split('v')[0]
			source_id = f'arxiv:{arxiv_id}'

			pdf_path = None
			if self.download_dir:
				pdf_path = self._download_pdf(paper, arxiv_id)

			citations = self._extract_citations(paper)

			result = SearchResult(
				source_id=source_id,
				title=paper.title,
				content=paper.summary,  # Abstract
				authors=[author.name for author in paper.authors],
				year=paper.published.year,
				url=paper.pdf_url,
				citations=citations,
				metadata={
					'arxiv_id': arxiv_id,
					'categories': paper.categories,
					'pdf_path': str(pdf_path) if pdf_path else None,
					'comment': paper.comment,
					'journal_ref': paper.journal_ref,
				},
			)

			results.append(result)

		logger.info(f'Found {len(results)} papers on arXiv')
		return results

	def supports_full_text(self) -> bool:
		return True

	def _download_pdf(self, paper: arxiv.Result, arxiv_id: str) -> Path | None:
		try:
			filename = f'{arxiv_id}.pdf'
			filepath = self.download_dir / filename  # type: ignore

			if filepath.exists():
				logger.debug(f'PDF already exists: {filename}')
				return filepath

			paper.download_pdf(dirpath=str(self.download_dir), filename=filename)
			logger.debug(f'Downloaded PDF: {filename}')
			return filepath

		except Exception as e:
			logger.warning(f'Failed to download PDF for {arxiv_id}: {e}')
			return None

	def _extract_citations(self, paper: arxiv.Result) -> list[CitationReference]:
		"""
		Extract citation references from paper.

		For now, returns empty list.
		Future: Parse PDF and extract reference section.

		This is where you'd use PDF parsing to find:
		- Reference section
		- Extract citation strings
		- Return as CitationReference objects
		"""
		# TODO: Implement PDF parsing for citations
		# This is a separate concern - can be added later
		return []


# ============================================================================
# PDF Citation Extraction (Placeholder for Future)
# ============================================================================


def extract_citations_from_pdf(pdf_path: Path) -> list[CitationReference]:
	"""
	Parse PDF and extract reference section.

	This is complex and belongs in a separate module.
	For MVP, we work with abstracts only.

	Future implementation would:
	1. Use PyMuPDF to extract text
	2. Find "References" section
	3. Parse citation strings
	4. Return as CitationReference objects
	"""
	# TODO: Implement this in a separate pdf_parser.py module
	return []
