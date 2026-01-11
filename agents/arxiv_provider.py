from pathlib import Path

from agents.search_provider import SearchProvider
from models import SearchResult
from search import ArxivSearch


class ArxivProvider(SearchProvider):
	def __init__(self, download_dir: Path | str | None = None):
		self.arxiv_search = ArxivSearch(download_dir=download_dir)

	def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
		return self.arxiv_search.search(query, max_results=max_results)

	def get_name(self) -> str:
		return 'arXiv'

	def supports_semantic_search(self) -> bool:
		return False
