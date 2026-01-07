import json
import uuid
import requests

from .base import SearchProvider
from src.models import SearchResult


class OpenRouterSearchProvider(SearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "xiaomi/mimo-v2-flash:free"

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research assistant. "
                    "Search the web for academic papers and extract key findings. "
                    "Return strictly valid JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Search for academic papers about: {query}\n\n"
                    f"Return {max_results} most relevant sources as JSON with fields:\n"
                    "- title\n"
                    "- authors\n"
                    "- year\n"
                    "- key_findings\n"
                    "- url"
                ),
            },
        ]

        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
            },
            timeout=60,
        )

        response.raise_for_status()
        data = response.json()

        return self._parse_openrouter_response(data)

    def supports_full_text(self) -> bool:
        return False

    def _parse_openrouter_response(self, data) -> list[SearchResult]:
        results: list[SearchResult] = []

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        try:
            parsed = json.loads(content)

            if isinstance(parsed, dict):
                parsed = parsed.get("results", parsed)

            for item in parsed:
                results.append(
                    SearchResult(
                        source_id=str(uuid.uuid4()),
                        title=item.get("title", "Unknown title"),
                        content=item.get("key_findings", ""),
                        authors=item.get("authors"),
                        year=item.get("year"),
                        url=item.get("url"),
                        citations=[],
                        metadata={
                            "provider": "openrouter",
                            "model": self.model,
                            "raw_item": item,
                        },
                    )
                )

            if results:
                return results

        except json.JSONDecodeError:
            pass

        # Fallback: unstructured text
        blocks = [b.strip() for b in content.split("\n\n") if b.strip()]

        for block in blocks:
            results.append(
                SearchResult(
                    source_id=str(uuid.uuid4()),
                    title="Unknown title",
                    content=block,
                    authors=None,
                    year=None,
                    url=None,
                    citations=[],
                    metadata={
                        "provider": "openrouter",
                        "model": self.model,
                        "raw_block": block,
                    },
                )
            )

        return results
