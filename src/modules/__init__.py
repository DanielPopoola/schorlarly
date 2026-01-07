from pathlib import Path
from src.config.settings import settings, get_embedding_provider, get_search_provider
from src.storage.claim import ClaimStore
from src.modules.claim_extractor import ClaimExtractor
from src.modules.research import ResearchModule


def create_research_module(storage_path: Path) -> ResearchModule:
    search_provider = get_search_provider()
    embedding_provider = get_embedding_provider()

    if settings.ANTHROPIC_API_KEY:
        from anthropic import Anthropic

        llm_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    elif settings.OPENAI_API_KEY:
        from openai import OpenAI

        llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    else:
        raise ValueError("No LLM API key configured")

    claim_extractor = ClaimExtractor(llm_client)
    claim_store = ClaimStore(storage_path, embedding_provider)

    return ResearchModule(
        search_provider=search_provider,
        claim_extractor=claim_extractor,
        claim_store=claim_store,
    )
