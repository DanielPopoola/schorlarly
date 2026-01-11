from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	ANTHROPIC_API_KEY: str | None = None
	OPENAI_API_KEY: str | None = None
	GEMINI_API_KEY: str | None = None
	OPENROUTER_API_KEY: str | None = None

	PERPLEXITY_API_KEY: str | None = None

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
	# EMBEDDING_MODEL: str = 'gemini-embedding-001'
	RESEARCH_MODEL: str = 'llama-3.1-sonar-large-128k-online'
	WRITING_MODEL: str = 'claude-3-5-sonnet-20241022'

	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


settings = Settings()
