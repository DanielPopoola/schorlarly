from src.modules.research.arXiv_search import ArxivSearch


def test_arxiv_search_basic():
	search = ArxivSearch()
	results = search.search('attention mechanisms', max_results=3)

	assert len(results) > 0
	assert all(r.source_id.startswith('arxiv:') for r in results)
	assert all(r.content for r in results)
	return [r.content for r in results]
