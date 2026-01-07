import json
import uuid
from openai import OpenAI

from .base import SearchProvider
from src.models import SearchResult


class PerplexitySearchProvider(SearchProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        self.model = "llama-3.1-sonar-large-128k-online"

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research assistant. Find academic papers and "
                    "extract key findings. Return results as structured JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Search for academic papers about: {query}\n\n"
                    f"Return {max_results} most relevant sources with:\n"
                    "- Title\n"
                    "- Authors (if available)\n"
                    "- Year\n"
                    "- Key findings/claims\n"
                    "- Source URL\n"
                    "\nReturn strictly valid JSON."
                ),
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model, messages=messages, return_citations=True
        )  # type: ignore

        return self._parse_perplexity_response(response)

    def supports_full_text(self) -> bool:
        return False

    def _parse_perplexity_response(self, response) -> list[SearchResult]:
        results: list[SearchResult] = []

        message = response.choices[0].message
        content = message.content or ""
        citations = getattr(response, "citations", []) or []

        try:
            parsed = json.loads(content)

            if isinstance(parsed, dict):
                parsed = parsed.get("results", [])

            for item in parsed:
                results.append(
                    SearchResult(
                        source_id=str(uuid.uuid4()),
                        title=item.get("title", "Unknown title"),
                        content=item.get("key_findings", "") or item.get("summary", ""),
                        authors=item.get("authors"),
                        year=item.get("year"),
                        url=item.get("url"),
                        citations=citations,
                        metadata={
                            "provider": "perplexity",
                            "raw_item": item,
                        },
                    )
                )

            if results:
                return results

        except json.JSONDecodeError:
            pass

        blocks = [b.strip() for b in content.split("\n\n") if b.strip()]

        for block in blocks:
            title = None
            year = None
            url = None

            lines = block.splitlines()

            if lines:
                title = lines[0].strip("•- ")

            for line in lines:
                if "http" in line:
                    url = line.strip()
                if line.strip().isdigit() and len(line.strip()) == 4:
                    year = int(line.strip())

            results.append(
                SearchResult(
                    source_id=str(uuid.uuid4()),
                    title=title or "Unknown title",
                    content=block,
                    authors=None,
                    year=year,
                    url=url,
                    citations=citations,
                    metadata={
                        "provider": "perplexity",
                        "raw_block": block,
                    },
                )
            )

        return results
