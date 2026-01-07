import json
from src.models import Section, GlobalState, SectionSummary, Finding
from src.utils.logger import logger
from typing import Any


class LedgerUpdater:
    def __init__(self, llm_client: Any, model: str):
        self.llm_client = llm_client
        self.model = model

    def update(self, section: Section, global_state: GlobalState) -> SectionSummary:
        """
        Summarizes the section and extracts key findings/terms to update the ledger.
        """
        logger.info(f"Updating ledger for Section {section.section_id}...")

        summary_prompt = f"""Summarize the following academic section in 150-200 words. 
Focus on the primary arguments, logical transitions, and key conclusions.

Section Title: {section.title}
Content:
{section.content}

Return ONLY the summary text."""

        summary_text = self._call_llm(summary_prompt, max_tokens=500)

        extraction_prompt = f"""Extract 3-5 key findings and any new key terms (with definitions) introduced in this section.

Section Content:
{section.content}

Return as valid JSON with this structure:
{{
  "key_findings": [
    {{
      "text": "Detailed finding text",
      "source_ids": ["List of source IDs cited for this finding"]
    }}
  ],
  "key_terms": {{
    "term": "clear definition"
  }}
}}
"""
        extraction_json = self._call_llm(extraction_prompt, max_tokens=1000)

        findings = []
        new_terms = {}

        try:
            data = json.loads(self._clean_json(extraction_json))
            findings = [
                Finding(
                    text=f["text"],
                    source_ids=f.get("source_ids", []),
                    section_id=section.section_id,
                )
                for f in data.get("key_findings", [])
            ]
            new_terms = data.get("key_terms", {})
        except Exception as e:
            logger.warning(f"Failed to parse findings/terms from LLM: {e}")

        if new_terms:
            global_state.key_terms.update(new_terms)
            logger.info(f"Added {len(new_terms)} new terms to global state.")

        summary = SectionSummary(
            section_id=section.section_id,
            section_title=section.title,
            summary=summary_text if summary_text else "Summary generation failed.",
            key_findings=findings,
            key_terms=list(new_terms.keys()),
        )

        global_state.section_summaries.append(summary)
        return summary

    def _call_llm(self, prompt: str, max_tokens: int) -> str:
        try:
            response = self.llm_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except AttributeError:
            pass

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except AttributeError:
            pass
        return ""

    def _clean_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
