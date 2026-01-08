from typing import Any, Literal

from src.utils.logger import logger


class UnifiedLLMClient:
	def __init__(self, client: Any, model: str, site_url: str | None = None, app_name: str | None = None):
		self.client = client
		self.model = model
		self.site_url = site_url
		self.app_name = app_name
		self.client_type = self._detect_client_type()

	def _detect_client_type(self) -> Literal['anthropic', 'openai', 'openrouter']:
		if hasattr(self.client, 'messages') and hasattr(self.client.messages, 'create'):
			return 'anthropic'

		if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
			base_url = str(getattr(self.client, 'base_url', ''))
			if 'openrouter.ai' in base_url:
				return 'openrouter'
			return 'openai'

		raise ValueError('Unsupported LLM client. Must be Anthropic, OpenAI, or OpenRouter instance.')

	def generate(self, prompt: str, max_tokens: int = 1000) -> str:
		try:
			if self.client_type == 'anthropic':
				return self._call_anthropic(prompt, max_tokens)
			elif self.client_type == 'openrouter':
				return self._call_openrouter(prompt, max_tokens)
			else:
				return self._call_openai(prompt, max_tokens)
		except Exception as e:
			logger.error(f'LLM generation failed ({self.client_type}): {e}')
			raise RuntimeError(f'Failed to generate text: {e}') from e

	def _call_anthropic(self, prompt: str, max_tokens: int) -> str:
		response = self.client.messages.create(
			model=self.model,
			max_tokens=max_tokens,
			messages=[{'role': 'user', 'content': prompt}],
		)
		return response.content[0].text

	def _call_openai(self, prompt: str, max_tokens: int) -> str:
		response = self.client.chat.completions.create(
			model=self.model,
			messages=[{'role': 'user', 'content': prompt}],
			max_tokens=max_tokens,
		)
		return response.choices[0].message.content

	def _call_openrouter(self, prompt: str, max_tokens: int) -> str:
		extra_headers = {}
		if self.site_url:
			extra_headers['HTTP-Referer'] = self.site_url
		if self.app_name:
			extra_headers['X-Title'] = self.app_name

		response = self.client.chat.completions.create(
			model=self.model,
			messages=[{'role': 'user', 'content': prompt}],
			max_tokens=max_tokens,
			extra_headers=extra_headers,
		)
		return response.choices[0].message.content
