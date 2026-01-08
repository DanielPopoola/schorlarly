import pytest
from pathlib import Path
from openai import OpenAI
from src.utils.llm_client import UnifiedLLMClient
from src.modules.research.arXiv_search import ArxivSearch
from src.modules.research.deduplication import PaperDeduplicator
from src.modules.claim_extractor import ClaimExtractor
from src.storage.claim import ClaimStore
from src.storage.state_store import StateStore
from src.models import GlobalState, EvidenceType
from src.config.settings import settings


@pytest.fixture
def temp_storage(tmp_path):
	storage = tmp_path / 'test_storage'
	storage.mkdir()
	return storage


@pytest.mark.skipif(not getattr(settings, 'OPENROUTER_API_KEY', None), reason='No LLM API key configured')
def test_full_research_pipeline(temp_storage):
	search = ArxivSearch(download_dir=temp_storage / 'papers')
	results = search.search('transformer attention mechanisms', max_results=3)

	assert len(results) > 0, 'Should find papers on arXiv'
	assert all(r.source_id.startswith('arxiv:') for r in results)
	assert all(r.content for r in results), 'All papers should have abstracts'

	dedup = PaperDeduplicator()
	unique_papers = dedup.deduplicate(results)

	raw_client = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=settings.OPENROUTER_API_KEY)

	llm_client = UnifiedLLMClient(
		client=raw_client,
		model='xiaomi/mimo-v2-flash:free',
		site_url='https://github.com/DanielPopoola/scholarly',
		app_name='Scholarly Test Suite',
	)

	extractor = ClaimExtractor(llm_client)

	all_claims = []
	for paper in unique_papers:
		claims = extractor.extract_from_search_result(paper)
		all_claims.extend(claims)

	assert len(all_claims) > 0, 'Should extract at least some claims'

	for claim in all_claims[:3]:
		assert claim.claim_id
		assert claim.source_id
		assert claim.statement
		assert isinstance(claim.evidence_type, EvidenceType)
		assert isinstance(claim.tags, list)

	from src.config.settings import get_embedding_provider

	embedding_provider = get_embedding_provider()

	claim_store = ClaimStore(temp_storage, embedding_provider)

	for claim in all_claims:
		claim_store.add(claim)

	assert (temp_storage / 'claims.faiss').exists()
	assert (temp_storage / 'claims.json').exists()

	query = 'attention mechanism in transformers'
	top_claims = claim_store.search(query, top_k=3)

	assert len(top_claims) > 0, 'Should find relevant claims'

	relevant_count = sum(
		1
		for c in top_claims
		if 'attention' in c.statement.lower()
		or 'transformer' in c.statement.lower()
		or 'attention' in c.tags
		or 'transformer' in c.tags
	)

	assert relevant_count > 0, 'At least one result should be semantically relevant'

	state_store = StateStore(temp_storage)

	initial_state = GlobalState(
		thesis='Transformers revolutionized NLP through attention mechanisms',
		key_terms={'attention': 'mechanism for weighting input relevance'},
		current_section_id=0,
	)

	state_store.save(initial_state)
	assert state_store.exists()

	loaded_state = state_store.load()
	assert loaded_state is not None
	assert loaded_state.thesis == initial_state.thesis
	assert loaded_state.key_terms == initial_state.key_terms


@pytest.mark.skipif(not getattr(settings, 'OPENROUTER_API_KEY', None), reason='No LLM API key configured')
def test_claim_retrieval_quality(temp_storage):
	from src.config.settings import get_embedding_provider

	embedding_provider = get_embedding_provider()
	claim_store = ClaimStore(temp_storage, embedding_provider)

	raw_client = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=settings.OPENROUTER_API_KEY)

	llm_client = UnifiedLLMClient(
		client=raw_client,
		model='google/gemini-2.0-flash-001',
		site_url='https://github.com/your-repo/scholarly',
		app_name='Scholarly Test Suite',
	)

	extractor = ClaimExtractor(llm_client)

	search = ArxivSearch()
	results = search.search('neural network optimization', max_results=2)

	# Extract and store
	for paper in results:
		claims = extractor.extract_from_search_result(paper)
		for claim in claims:
			claim_store.add(claim)

	# Test different query types
	test_queries = [
		('learning rate schedules', 'optimization'),
		('gradient descent variants', 'optimization'),
		('training deep networks', 'training'),
	]

	print('\n' + '=' * 60)
	print('SEMANTIC SEARCH QUALITY TEST')
	print('=' * 60)

	for query, expected_topic in test_queries:
		results = claim_store.search(query, top_k=2)

		print(f"\nQuery: '{query}'")
		print(f'Expected topic: {expected_topic}')

		if results:
			print(f'Top result: {results[0].statement[:80]}...')

			# Check if result is topically relevant
			is_relevant = (
				expected_topic.lower() in results[0].statement.lower()
				or expected_topic.lower() in ' '.join(results[0].tags).lower()
			)

			print(f'Relevant: {"✓" if is_relevant else "✗"}')
		else:
			print('No results found')

	print('=' * 60)


def test_claim_store_persistence(temp_storage):
	from src.config.settings import get_embedding_provider
	from src.models import Claim, EvidenceType

	embedding_provider = get_embedding_provider()

	store1 = ClaimStore(temp_storage, embedding_provider)

	test_claims = [
		Claim(
			claim_id='test_001',
			source_id='test_paper',
			statement='Neural networks learn hierarchical representations',
			context='Deep learning fundamentals',
			evidence_type=EvidenceType.THEORETICAL_CLAIM,
			tags=['neural', 'networks', 'hierarchical'],
			page_number=None,
			section_in_source='Introduction',
		),
		Claim(
			claim_id='test_002',
			source_id='test_paper',
			statement='Gradient descent minimizes loss functions',
			context='Optimization basics',
			evidence_type=EvidenceType.METHODOLOGICAL,
			tags=['gradient', 'descent', 'optimization'],
			page_number=None,
			section_in_source='Methods',
		),
	]

	for claim in test_claims:
		store1.add(claim)

	store2 = ClaimStore(temp_storage, embedding_provider)

	retrieved_claim = store2.get('test_001')
	assert retrieved_claim is not None
	assert retrieved_claim.statement == test_claims[0].statement

	results = store2.search('neural networks', top_k=1)
	assert len(results) > 0
