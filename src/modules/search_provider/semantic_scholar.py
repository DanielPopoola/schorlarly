import requests
from .base import SearchProvider
from src.models import SearchResult


class SemanticScholarProvider(SearchProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.base_url = "https://api.semanticscholar.org/graph/v1"

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,authors,year,abstract,citationCount,url,paperId",
        }

        response = requests.get(
            f"{self.base_url}/paper/search", params=params, headers=headers
        )
        response.raise_for_status()

        data = response.json()
        return [
            SearchResult(
                source_id=paper["paperId"],
                title=paper["title"],
                content=paper.get("abstract", ""),
                authors=[a["name"] for a in paper.get("authors", [])],
                year=paper.get("year"),
                url=paper.get("url"),
                citations=[],  # Would need separate API call
                metadata={"citation_count": paper.get("citationCount", 0)},
            )
            for paper in data.get("data", [])
        ]

    def supports_full_text(self) -> bool:
        return False
