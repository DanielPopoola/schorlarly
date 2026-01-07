from abc import ABC, abstractmethod
from src.models import SearchResult


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    def supports_full_text(self) -> bool:
        raise NotImplementedError
