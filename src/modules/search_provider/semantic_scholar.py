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
            f"{self.base_url}/paper/search",
            params=params,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        results: list[SearchResult] = []

        for paper in data.get("data", []):
            paper_id = paper["paperId"]

            citations = self._fetch_citations(
                paper_id=paper_id,
                limit=5,  # hard cap for safety
            )

            results.append(
                SearchResult(
                    source_id=paper_id,
                    title=paper["title"],
                    content=paper.get("abstract", ""),
                    authors=[a["name"] for a in paper.get("authors", [])],
                    year=paper.get("year"),
                    url=paper.get("url"),
                    citations=citations,
                    metadata={
                        "citation_count": paper.get("citationCount", 0),
                        "provider": "semantic_scholar",
                    },
                )
            )

        return results

    def supports_full_text(self) -> bool:
        return False

    def _fetch_citations(self, paper_id: str, limit: int = 5) -> list[str]:
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        params = {
            "limit": limit,
            "fields": "citingPaper.paperId,citingPaper.url",
        }

        response = requests.get(
            f"{self.base_url}/paper/{paper_id}/citations",
            params=params,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()

        citations: list[str] = []
        for item in data.get("data", []):
            paper = item.get("citingPaper", {})
            url = paper.get("url") or paper.get("paperId")
            if url:
                citations.append(url)

        return citations
