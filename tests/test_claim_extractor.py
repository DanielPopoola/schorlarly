import pytest
import json
from unittest.mock import Mock
from src.modules.claim_extractor import ClaimExtractor
from src.models import SearchResult, EvidenceType
from src.utils.llm_client import UnifiedLLMClient


@pytest.fixture
def mock_raw_anthropic_client():
	client = Mock()

	mock_content = Mock()
	mock_content.text = json.dumps(
		{
			'claims': [
				{
					'statement': 'Transformer achieved 92% accuracy on ImageNet',
					'evidence_type': 'empirical_finding',
					'context': 'Using 1B tokens for training',
					'page_number': None,
					'section': 'Abstract',
				}
			]
		}
	)

	mock_response = Mock()
	mock_response.content = [mock_content]

	client.messages.create.return_value = mock_response
	return client


def test_claim_extraction_basic(mock_raw_anthropic_client):
	unified_client = UnifiedLLMClient(client=mock_raw_anthropic_client, model='claude-3')

	extractor = ClaimExtractor(unified_client)

	result = SearchResult(
		source_id='arxiv:2301.12345',
		title='Test Paper',
		content='Abstract about transformers...',
		authors=['Dr. Smith'],
		year=2023,
		url='https://arxiv.org/pdf/2301.12345',
		citations=[],
		metadata={},
	)

	claims = extractor.extract_from_search_result(result)

	assert len(claims) == 1
	assert claims[0].claim_id == 'arxiv:2301.12345_claim_000'
	assert claims[0].evidence_type == EvidenceType.EMPIRICAL_FINDING
	assert 'transformer' in claims[0].statement.lower()
