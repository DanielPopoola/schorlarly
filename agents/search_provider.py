from abc import ABC, abstractmethod

from models import SearchResult


class SearchProvider(ABC):
	@abstractmethod
	def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
		pass

	@abstractmethod
	def get_name(self) -> str:
		pass

	def supports_semantic_search(self) -> bool:
		return False
