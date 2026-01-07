import re
from src.utils.logger import logger
from typing import Any
from datetime import datetime, UTC
from src.models import Citation, Section, SectionStatus


class DraftingEngine:
    def __init__(self, llm_client: Any, model: str):
        self.llm_client = llm_client
        self.model = model

    def draft(self, prompt: str) -> str:
        logger.debug(f"Calling LLM ({self.model}) for drafting...")
        try:
            response = self.llm_client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except AttributeError:
            pass

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
            )
            return response.choices[0].message.content
        except AttributeError:
            pass

        raise ValueError("LLM client not supported or failed to provide a response")


class SectionParser:
    def parse(self, text: str, section_id: int) -> Section:
        citation_pattern = r'\[(.*?):\s*"(.*?)"\]'
        matches = re.finditer(citation_pattern, text)

        citations = []
        for match in matches:
            claim_id = match.group(1).strip()
            quoted_text = match.group(2).strip()
            citations.append(
                Citation(
                    claim_id=claim_id,
                    quoted_text=quoted_text,
                    location_in_section=match.start(),
                )
            )

        word_count = len(text.split())

        return Section(
            section_id=section_id,
            title="",
            content=text,
            citations=citations,
            word_count=word_count,
            status=SectionStatus.DRAFT,
            created_at=datetime.now(UTC).isoformat(),
        )
