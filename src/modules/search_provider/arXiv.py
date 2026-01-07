import arxiv
from .base import SearchProvider
from src.models import SearchResult


class ArxivProvider(SearchProvider):
    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
        )

        results = []
        for paper in client.results(search):
            results.append(
                SearchResult(
                    source_id=paper.entry_id,
                    title=paper.title,
                    content=paper.summary,
                    authors=[a.name for a in paper.authors],
                    year=paper.published.year,
                    url=paper.pdf_url,
                    citations=[],
                    metadata={"categories": paper.categories},
                )
            )

        return results

    def supports_full_text(self) -> bool:
        return True
