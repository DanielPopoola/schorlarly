from typing import Any
from dataclasses import dataclass
from src.models import SectionSummary, Claim


@dataclass
class DraftingContext:
    thesis: str
    relevant_summaries: list[SectionSummary]
    previous_section_text: str | None
    relevant_claims: list[Claim]
    key_terms: dict[str, str]
    questions: list[str]
    section_id: int
    section_title: str


def build_drafting_prompt(context: Any) -> str:
    claims_str = ""
    for c in context.relevant_claims:
        claims_str += f"- Claim ID: {c.claim_id}\n"
        claims_str += f"  Statement: {c.statement}\n"
        if c.context:
            claims_str += f"  Context: {c.context}\n"
        claims_str += f"  Source: {c.source_id}\n\n"

    summaries_str = ""
    for s in context.relevant_summaries:
        summaries_str += f"Summary of Section {s.section_id}: {s.section_title}\n"
        summaries_str += f"{s.summary}\n\n"

    terms_str = "\n".join([f"- {k}: {v}" for k, v in context.key_terms.items()])

    questions_str = "\n".join(
        [f"{i + 1}. {q}" for i, q in enumerate(context.questions)]
    )

    prompt = f"""You are an expert academic writer. Your task is to draft a high-quality research paper section.

TARGET SECTION: Section {context.section_id}: {context.section_title}
WORD COUNT GOAL: 1000-1500 words

### PAPER THESIS
{context.thesis}

### CONTEXT FROM RELATED PREVIOUS SECTIONS
{summaries_str if summaries_str else "No previous sections yet."}

### TRANSITION FROM PREVIOUSLY WRITTEN TEXT
{context.previous_section_text if context.previous_section_text else "This is the start of the paper or a new major division."}

### QUESTIONS TO BE ANSWERED IN THIS SECTION
{questions_str}

### AVAILABLE CLAIMS (ONLY CITE FROM THIS LIST)
{claims_str if claims_str else "No specific claims provided. Base your writing on established knowledge while maintaining academic rigor."}

### KEY TERMS AND DEFINITIONS TO MAINTAIN CONSISTENCY
{terms_str if terms_str else "No specific key terms defined yet."}

### WRITING INSTRUCTIONS
1. TONE: Professional, objective, and analytical academic prose.
2. CONTENT: Thoroughly answer all questions provided above. 
3. STRUCTURE: Use appropriate subsections and logical flow.
4. CITATION RULE: Every time you use information from the "AVAILABLE CLAIMS" list, you MUST cite it using the exact format: [ClaimID: "quoted text"].
Example: The bioaccumulation of microplastics has been shown to disrupt marine food chains [Smith2023_claim_001: "73% of fish samples contain microplastics"].
5. NO HALLUCINATION: Only use Claim IDs provided in the list above. Do not invent Claim IDs or sources.
6. LENGTH: Aim for 1000-1500 words. Be comprehensive and detailed.
7. TRANSITION: Ensure a smooth flow from the previous text provided.

Draft the section content now. Begin directly with the section body.
"""
    return prompt
