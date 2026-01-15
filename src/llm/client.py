import logging
from enum import Enum
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
	OPENROUTER = 'openrouter'
	ANTHROPIC = 'anthropic'


class LLMClient:
	def __init__(self, provider: str, model: str, api_key: str, temperature: float = 0.7, max_tokens: int = 4000):
		self.provider = LLMProvider(provider)
		self.model = model
		self.api_key = api_key
		self.temperature = temperature
		self.max_tokens = max_tokens

		self.total_input_tokens = 0
		self.total_output_tokens = 0

		self._client = self._initialize_client()
		logger.info(f'LLM Client initialized: {provider}/{model}')

	def _initialize_client(self):
		if self.provider == LLMProvider.OPENROUTER:
			from openai import OpenAI

			return OpenAI(base_url='https://openrouter.ai/api/v1', api_key=self.api_key)
		elif self.provider == LLMProvider.ANTHROPIC:
			from anthropic import Anthropic

			return Anthropic(api_key=self.api_key)
		else:
			raise ValueError(f'Unsupported provider: {self.provider}')

	@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10), reraise=True)
	def generate(
		self,
		prompt: str,
		system_prompt: str | None = None,
		temperature: float | None = None,
		max_tokens: int | None = None,
	) -> str:
		temp = temperature if temperature is not None else self.temperature
		max_tok = max_tokens if max_tokens is not None else self.max_tokens
		logger.info(f'Generating with {self.provider.value}...')

		try:
			if self.provider == LLMProvider.OPENROUTER:
				response = self._generate_openrouter(prompt, system_prompt, temp, max_tok)
			else:
				response = self._generate_anthropic(prompt, system_prompt, temp, max_tok)

			logger.info(
				f'Generation complete. Tokens used: input={self.total_input_tokens}, output={self.total_output_tokens}'
			)

			return response

		except Exception as e:
			logger.error(f'Generation failed: {e}')
			raise

	def _generate_openrouter(
		self, prompt: str, system_prompt: str | None = None, temperature: float = 0.7, max_tokens: int = 4000
	) -> str:
		messages = []

		if system_prompt:
			messages.append({'role': 'system', 'content': system_prompt})

		messages.append({'role': 'user', 'content': prompt})

		response = self._client.chat.completions.create(
			model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens
		)

		# Track usage
		if hasattr(response, 'usage') and response.usage:
			self.total_input_tokens += response.usage.prompt_tokens
			self.total_output_tokens += response.usage.completion_tokens

		return response.choices[0].message.content

	def _generate_anthropic(self, prompt: str, system_prompt: str | None, temperature: float, max_tokens: int) -> str:
		kwargs = {
			'model': self.model,
			'max_tokens': max_tokens,
			'temperature': temperature,
			'messages': [{'role': 'user', 'content': prompt}],
		}

		if system_prompt:
			kwargs['system'] = system_prompt

		response = self._client.messages.create(**kwargs)

		return response.content[0].text

	def get_usage_stats(self) -> dict[str, int]:
		"""Get token usage statistics."""
		return {
			'input_tokens': self.total_input_tokens,
			'output_tokens': self.total_output_tokens,
			'total_tokens': self.total_input_tokens + self.total_output_tokens,
		}


def create_llm_client_from_config(config: dict[str, Any]) -> LLMClient:
	return LLMClient(
		provider=config['provider'],
		model=config['model'],
		api_key=config['api_key'],
		temperature=config.get('temperature', 0.7),
		max_tokens=config.get('max_tokens', 4000),
	)
