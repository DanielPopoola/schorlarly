from typing import Any, Literal

from src.utils.logger import logger


class UnifiedLLMClient:
	def __init__(self, client: Any, model: str):
		self.client = client
		self.model = model
		self.client_type = self._detect_client_type()

	def _detect_client_type(self) -> Literal['anthropic', 'openai']:
		if hasattr(self.client, 'messages') and hasattr(self.client.messages, 'create'):
			return 'anthropic'
		elif hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
			return 'openai'
		else:
			raise ValueError('Unsupported LLM client. Must be Anthropic or OpenAI instance.')

	def generate(self, prompt: str, max_tokens: int = 1000) -> str:
		try:
			if self.client_type == 'anthropic':
				return self._call_anthropic(prompt, max_tokens)
			else:
				return self._call_openai(prompt, max_tokens)
		except Exception as e:
			logger.error(f'LLM generation failed: {e}')
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
