import datetime
from typing import Any
from src.models import (
    Section,
    IssueType,
    Severity,
    ValidationIssue,
    ValidationResult,
)
from src.storage.claim import ClaimStore
from src.utils.logger import logger
from src.modules.validation.citation import CitationValidator
from src.modules.validation.content import ContentValidator


class ValidationModule:
    def __init__(self, claim_store: ClaimStore, llm_client: Any, model: str):
        self.citation_validator = CitationValidator(claim_store)
        self.content_validator = ContentValidator(llm_client, model)

    def validate_section(
        self, section: Section, questions: list[str], attempt: int = 1
    ) -> ValidationResult:
        logger.info(
            f"Validating Section {section.section_id}: {section.title} (Attempt {attempt})"
        )

        issues: list[ValidationIssue] = []

        # 1. Citation Validation
        citation_issues = self.citation_validator.validate(section)
        issues.extend(citation_issues)

        # Early exit if critical citation issues
        if any(i.severity == Severity.CRITICAL for i in citation_issues):
            logger.warning(
                f"Critical citation issues found for Section {section.section_id}. Skipping further content validation."
            )
            return ValidationResult(
                validation_id=f"val-{section.section_id}-{attempt}-{datetime.datetime.now().timestamp()}",
                section_id=section.section_id,
                passed=False,
                issues=issues,
                attempt=attempt,
                timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            )

        # 2. Content and Style Validation (LLM-based, combined)
        content_style_issues = self.content_validator.validate(section, questions)
        issues.extend(content_style_issues)

        # 3. Word Count Validation
        min_words, max_words = 1000, 1500  # Should be configurable via settings
        if not (min_words <= section.word_count <= max_words):
            issues.append(
                ValidationIssue(
                    issue_type=IssueType.WORD_COUNT,
                    severity=Severity.WARNING,  # Can be CRITICAL if strict
                    message=f"""Section word count ({section.word_count}) is outside the target range ({min_words}-{max_words}).""",
                    suggestion=f"""Adjust section length to be between {min_words} and {max_words} words.""",
                    location="",
                )
            )

        # Determine pass/fail based on CRITICAL issues
        passed = not any(issue.severity == Severity.CRITICAL for issue in issues)

        return ValidationResult(
            validation_id=f"val-{section.section_id}-{attempt}-{datetime.datetime.now().timestamp()}",
            section_id=section.section_id,
            passed=passed,
            issues=issues,
            attempt=attempt,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        )
