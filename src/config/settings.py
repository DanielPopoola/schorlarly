from enum import Enum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.storage.embedding import (
	EmbeddingProvider,
	GeminiEmbeddings,
	HuggingFaceEmbeddings,
	OpenAIEmbeddings,
	SentenceTransformerEmbeddings,
)


class SearchBackend(Enum):
	PERPLEXITY = 'perplexity'
	SEMANTIC_SCHOLAR = 'semantic_scholar'
	ARXIV = 'arxiv'
	OPENROUTER = 'open_router'


class Settings(BaseSettings):
	ANTHROPIC_API_KEY: str | None = None
	OPENAI_API_KEY: str | None = None
	GEMINI_API_KEY: str | None = None
	OPENROUTER_API_KEY: str | None = None

	# Research settings
	SEARCH_BACKEND: str = 'open_router'
	PERPLEXITY_API_KEY: str | None = None
	SEMANTIC_SCHOLAR_API_KEY: str | None = None
	MAX_PAPERS_PER_QUERY: int = 10

	HUGGINGFACE_API_TOKEN: str = ''
	HUGGINGFACE_MODEL: str = ''

	# App Settings
	APP_NAME: str = 'Scholarly'
	LOG_LEVEL: str = 'INFO'

	# Paths
	BASE_DIR: Path = Path(__file__).parent.parent.parent
	DATA_DIR: Path = BASE_DIR / 'data'
	STORAGE_PATH: Path = DATA_DIR / 'storage'
	OUTPUT_DIR: Path = DATA_DIR / 'outputs'

	# LLM Models
	EMBEDDING_MODEL: str = 'sentence-transformers/all-MiniLM-L6-v2'
	RESEARCH_MODEL: str = 'llama-3.1-sonar-large-128k-online'
	WRITING_MODEL: str = 'claude-3-5-sonnet-20241022'

	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


def get_embedding_provider() -> EmbeddingProvider:
	if settings.OPENAI_API_KEY and 'openai' in settings.EMBEDDING_MODEL.lower():
		return OpenAIEmbeddings(settings.OPENAI_API_KEY)
	elif settings.GEMINI_API_KEY and 'gemini' in settings.EMBEDDING_MODEL.lower():
		return GeminiEmbeddings(settings.GEMINI_API_KEY)
	elif settings.ANTHROPIC_API_KEY and 'huggingface' in settings.EMBEDDING_MODEL.lower():
		return HuggingFaceEmbeddings(settings.HUGGINGFACE_API_TOKEN)
	else:
		return SentenceTransformerEmbeddings(settings.EMBEDDING_MODEL)


settings = Settings()
