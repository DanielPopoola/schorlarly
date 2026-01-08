from typing import Protocol, runtime_checkable

from src.models import SearchResult


@runtime_checkable
class ResearchSearchProvider(Protocol):
	def search(self, query: str, max_results: int = 10) -> list[SearchResult]: ...

	def supports_full_text(self) -> bool: ...


def validate_search_provider(provider: object) -> bool:
	return isinstance(provider, ResearchSearchProvider)
