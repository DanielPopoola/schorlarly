import json

from src.models import Claim, EvidenceType, SearchResult
from src.utils.llm_client import UnifiedLLMClient
from src.utils.logger import logger


class ClaimExtractor:
	def __init__(self, llm_client: UnifiedLLMClient):
		self.llm_client = llm_client

	def extract_from_search_result(self, result: SearchResult) -> list[Claim]:
		logger.info(f'Extracting claims from: {result.title[:60]}...')

		prompt = self._build_extraction_prompt(result)

		try:
			response_text = self.llm_client.generate(prompt, max_tokens=2000)

			claims_data = self._parse_llm_response(response_text)

			claims = self._convert_to_claims(claims_data, result)

			logger.info(f'  Extracted {len(claims)} claims from {result.source_id}')
			return claims

		except Exception as e:
			logger.error(f'Failed to extract claims from {result.source_id}: {e}')
			return []

	def _build_extraction_prompt(self, result: SearchResult) -> str:
		return f"""You are a research assistant extracting factual claims from academic papers.

# PAPER INFORMATION

Title: {result.title}
Authors: {', '.join(result.authors or ['Unknown'])}
Year: {result.year or 'Unknown'}

Content:
{result.content}

---

# YOUR TASK

Extract 5-15 factual claims from this paper. Each claim should be:
- **Atomic**: One fact per claim (not compound statements)
- **Factual**: Verifiable, not opinions or interpretations
- **Self-contained**: Understandable without reading the full paper
- **Citable**: Something you'd reference in a research paper

# EVIDENCE TYPES

Classify each claim as one of:
- **empirical_finding**: Experimental results, observations
- **statistical_result**: Numerical data, percentages, measurements
- **theoretical_claim**: Hypotheses, proposed explanations
- **methodological**: How research was conducted
- **background**: Context, definitions, prior work

# OUTPUT FORMAT

Return ONLY valid JSON (no markdown, no explanations):

{{
  "claims": [
    {{
      "statement": "The main finding in 1-2 clear sentences",
      "evidence_type": "empirical_finding|statistical_result|theoretical_claim|methodological|background",
      "context": "Additional context explaining this claim (optional but recommended)",
      "page_number": null,
      "section": "Abstract|Introduction|Methods|Results|Discussion|etc"
    }}
  ]
}}

# EXAMPLE

Good claim:
{{
  "statement": "Transformer models achieved 92% accuracy on ImageNet classification",
  "evidence_type": "empirical_finding",
  "context": "Performance metric from experiment using 1 billion training tokens",
  "page_number": null,
  "section": "Abstract"
}}

Bad claim (too vague):
{{
  "statement": "The model worked well",
  "evidence_type": "empirical_finding",
  "context": null,
  "page_number": null,
  "section": "Abstract"
}}

---

Now extract claims from the paper above. Return ONLY the JSON.
"""

	def _parse_llm_response(self, response: str) -> dict:
		response = response.strip()
		if response.startswith('```json'):
			response = response[7:]
		if response.startswith('```'):
			response = response[3:]
		if response.endswith('```'):
			response = response[:-3]
		response = response.strip()

		try:
			data = json.loads(response)

			if 'claims' not in data:
				logger.warning("LLM response missing 'claims' field")
				return {'claims': []}

			if not isinstance(data['claims'], list):
				logger.warning("'claims' field is not a list")
				return {'claims': []}

			return data

		except json.JSONDecodeError as e:
			logger.error(f'Failed to parse LLM JSON: {e}')
			logger.debug(f'Response was: {response[:500]}')
			return {'claims': []}

	def _convert_to_claims(self, claims_data: dict, result: SearchResult) -> list[Claim]:
		claims: list[Claim] = []

		for idx, claim_dict in enumerate(claims_data.get('claims', [])):
			try:
				claim_id = f'{result.source_id}_claim_{idx:03d}'

				evidence_type_str = claim_dict.get('evidence_type', 'background')
				try:
					evidence_type = EvidenceType(evidence_type_str)
				except ValueError:
					logger.warning(f"Invalid evidence_type '{evidence_type_str}', defaulting to BACKGROUND")
					evidence_type = EvidenceType.BACKGROUND

				claim = Claim(
					claim_id=claim_id,
					source_id=result.source_id,
					statement=claim_dict['statement'],
					context=claim_dict.get('context'),
					evidence_type=evidence_type,
					tags=self._extract_tags(claim_dict['statement']),
					page_number=claim_dict.get('page_number'),
					section_in_source=claim_dict.get('section'),
					confidence=1.0,
					extracted_at=None,  # Could add timestamp here
				)

				claims.append(claim)

			except KeyError as e:
				logger.warning(f'Claim missing required field {e}, skipping')
				continue
			except Exception as e:
				logger.error(f'Failed to create Claim object: {e}')
				continue

		return claims

	def _extract_tags(self, statement: str) -> list[str]:
		words = statement.lower().split()
		tags = [w.strip('.,!?;:()[]{}') for w in words if len(w) > 4]

		seen = set()
		unique_tags = []
		for tag in tags:
			if tag not in seen:
				unique_tags.append(tag)
				seen.add(tag)

		return unique_tags[:10]
