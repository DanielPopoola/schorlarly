import re
from src.models import (
    Section,
    IssueType,
    Severity,
    ValidationIssue,
)
from src.storage.claim import ClaimStore


class CitationValidator:
    def __init__(self, claim_store: ClaimStore):
        self.claim_store = claim_store

    def validate(self, section: Section) -> list[ValidationIssue]:
        citation_issues: list[ValidationIssue] = []

        for citation in section.citations:
            claim = self.claim_store.get(citation.claim_id)

            if not claim:
                citation_issues.append(
                    ValidationIssue(
                        issue_type=IssueType.CITATION_MISSING,
                        severity=Severity.CRITICAL,
                        message=f"Claim ID '{citation.claim_id}' not found in ClaimStore.",
                        suggestion="Ensure all cited Claim IDs exist in the ClaimStore.",
                        location=f"Char: {citation.location_in_section}",
                    )
                )
                continue

            normalized_cited_quote = self._normalize_text(citation.quoted_text)
            normalized_claim_statement = self._normalize_text(claim.statement)

            if normalized_cited_quote not in normalized_claim_statement:
                citation_issues.append(
                    ValidationIssue(
                        issue_type=IssueType.CITATION_QUOTE_MISMATCH,
                        severity=Severity.CRITICAL,
                        message=(
                            f"Quoted text '{citation.quoted_text}' does not exactly match "
                            f"original claim statement for ID '{citation.claim_id}'."
                            f"Expected (normalized): '{normalized_claim_statement}', "
                            f"Got (normalized): '{normalized_cited_quote}'"
                        ),
                        suggestion=f"Ensure quoted text is an exact snippet or very close paraphrase of the original claim: '{claim.statement}'",
                        location=f"Char: {citation.location_in_section}",
                    )
                )

        # Check for original LLM format: [ClaimID: "exact quote"]
        # This regex ensures the full pattern is matched, not just parts.
        # re.findall(r'[[^]]*?:\s*".*?"', section.content)
        for match in re.finditer(r'[[^]]*?:\s*".*?"', section.content):
            full_citation_text = match.group(0)
            claim_id_part = match.group(1)
            quoted_text_part = match.group(2)

            # Further validate parts if needed, but basic format is captured by regex
            if not (claim_id_part and quoted_text_part):
                citation_issues.append(
                    ValidationIssue(
                        issue_type=IssueType.CITATION_INVALID,
                        severity=Severity.CRITICAL,
                        message=f"""Citation format "{full_citation_text}" is invalid. Expected [ClaimID: 'quoted text'].""",
                        suggestion="Correct the citation format to [ClaimID: 'quoted text'].",
                        location="Char: {match.start()}",
                    )
                )

        return citation_issues

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
