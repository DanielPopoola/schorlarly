import pytest
from unittest.mock import MagicMock
from src.modules.writing import WritingModule
from src.models import GlobalState, SectionStatus, EvidenceType, Claim
from src.storage.claim import ClaimStore
from src.storage.embedding import EmbeddingProvider


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    # Mock for Anthropic-style client
    client.messages.create.return_value.content = [
        MagicMock(
            text='This is a drafted section content with a citation [claim_001: "data shows 40%"]'
        )
    ]
    return client


@pytest.fixture
def mock_embedding_provider():
    provider = MagicMock(spec=EmbeddingProvider)
    provider.dimension.return_value = 384
    provider.encode.return_value = [0.1] * 384
    return provider


@pytest.fixture
def mock_claim_store():
    store = MagicMock(spec=ClaimStore)
    store.search.return_value = [
        Claim(
            claim_id="claim_001",
            source_id="source_1",
            statement="data shows 40% decline",
            context="in the ocean",
            evidence_type=EvidenceType.EMPIRICAL_FINDING,
            tags=["decline", "ocean"],
            page_number=1,
            section_in_source="Results",
        )
    ]
    return store


def test_writing_module_basic(
    mock_llm_client, mock_embedding_provider, mock_claim_store
):
    module = WritingModule(
        claim_store=mock_claim_store,
        embedding_provider=mock_embedding_provider,
        llm_client=mock_llm_client,
        model="test-model",
    )

    global_state = GlobalState(
        thesis="Microplastics are bad.",
        key_terms={},
        section_summaries=[],
        decisions_made=[],
        current_section_id=1,
        total_tokens_used=0,
        cost_usd=0.0,
        retry_counts={},
    )

    section, summary = module.write_section(
        section_id=1,
        section_title="Introduction",
        questions=["What are microplastics?"],
        global_state=global_state,
    )

    assert section.section_id == 1
    assert section.title == "Introduction"
    assert "claim_001" in [c.claim_id for c in section.citations]
    assert len(global_state.section_summaries) == 1
    assert summary.section_id == 1
