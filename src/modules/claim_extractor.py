import json
from typing import Any
from src.models import Claim, EvidenceType, SearchResult
from src.utils.logger import logger


class ClaimExtractor:
    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def extract_from_search_result(self, result: SearchResult) -> list[Claim]:
        prompt = self._build_extraction_prompt(result)

        try:
            response = self._call_llm(prompt)
            claims_data = self._parse_llm_response(response)
            claims = self._convert_to_claims(claims_data, result)

            logger.info(f"Extracted {len(claims)} claims from {result.source_id}")
            return claims

        except Exception as e:
            logger.error(f"Failed to extract claims from {result.source_id}: {e}")
            return []

    def _build_extraction_prompt(self, result: SearchResult) -> str:
        """Build the LLM prompt for claim extraction"""
        return f"""You are a research assistant extracting key claims from academic sources.

Given the following research source, extract all significant claims as structured JSON.

Source Information:
- Title: {result.title}
- Authors: {", ".join(result.authors or ["Unknown"])}
- Year: {result.year or "Unknown"}

Content:
{result.content}

Extract claims and return ONLY valid JSON in this exact format:
{{
  "claims": [
    {{
      "statement": "The main finding or claim (1-2 sentences)",
      "evidence_type": "empirical_finding|statistical_result|theoretical_claim|methodological|background",
      "context": "Additional context explaining the claim (optional)",
      "page_number": null,
      "section": "Results|Methods|Discussion|etc (if known)"
    }}
  ]
}}

Rules:
1. Only extract factual claims, not opinions
2. Each claim should be self-contained and clear
3. Prefer empirical findings and statistical results
4. Include 3-10 claims per source
5. Return ONLY the JSON, no additional text

JSON:"""

    def _call_llm(self, prompt: str) -> str:
        try:
            response = self.llm_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except AttributeError:
            pass
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except AttributeError:
            pass

        raise ValueError("LLM client format not recognized")

    def _parse_llm_response(self, response: str) -> dict:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        if response.startswith("```"):
            response = response[3:]  # Remove ```
        if response.endswith("```"):
            response = response[:-3]  # Remove ```

        response = response.strip()

        try:
            data = json.loads(response)

            if "claims" not in data:
                raise ValueError("Response missing 'claims' field")

            if not isinstance(data["claims"], list):
                raise ValueError("'claims' must be a list")

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return {"claims": []}  # Return empty instead of crashing

    def _convert_to_claims(
        self, claims_data: dict, result: SearchResult
    ) -> list[Claim]:
        claims = []

        for idx, claim_dict in enumerate(claims_data.get("claims", [])):
            try:
                claim_id = f"{result.source_id}_claim_{idx:03d}"

                evidence_type_str = claim_dict.get("evidence_type", "background")
                try:
                    evidence_type = EvidenceType(evidence_type_str)
                except ValueError:
                    logger.warning(
                        f"Invalid evidence_type '{evidence_type_str}', "
                        f"defaulting to BACKGROUND"
                    )
                    evidence_type = EvidenceType.BACKGROUND

                claim = Claim(
                    claim_id=claim_id,
                    source_id=result.source_id,
                    statement=claim_dict["statement"],
                    context=claim_dict.get("context"),
                    evidence_type=evidence_type,
                    tags=self._extract_tags(claim_dict["statement"]),
                    page_number=claim_dict.get("page_number"),
                    section_in_source=claim_dict.get("section"),
                    confidence=1.0,
                    extracted_at=None,  # Could add timestamp here
                )

                claims.append(claim)

            except KeyError as e:
                logger.warning(f"Claim missing required field {e}, skipping")
                continue
            except Exception as e:
                logger.error(f"Failed to create Claim object: {e}")
                continue

        return claims

    def _extract_tags(self, statement: str) -> list[str]:
        words = statement.lower().split()
        tags = [w.strip(".,!?;:()[]{}") for w in words if len(w) > 4]
        return list(dict.fromkeys(tags))[:10]
