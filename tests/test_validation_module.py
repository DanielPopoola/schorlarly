import pytest
from unittest.mock import MagicMock
from src.modules.validation import ValidationModule, CitationValidator, ContentValidator
from src.models import Section, Claim, IssueType, Severity, Citation, EvidenceType
from src.storage.claim import ClaimStore
import datetime
import re
import json


@pytest.fixture
def mock_claim_store():
    store = MagicMock(spec=ClaimStore)
    store.get.side_effect = {
        "claim_001": Claim(
            claim_id="claim_001",
            source_id="source_1",
            statement="Fish populations declined 40% in coastal regions due to microplastics.",
            context="A study conducted over 5 years",
            evidence_type=EvidenceType.EMPIRICAL_FINDING,
            tags=[],
            page_number=1,
            section_in_source="Results",
        ),
        "claim_002": Claim(
            claim_id="claim_002",
            source_id="source_2",
            statement="Microplastics accumulate in trophic levels.",
            context="Observation in lab studies",
            evidence_type=EvidenceType.EMPIRICAL_FINDING,
            tags=[],
            page_number=2,
            section_in_source="Discussion",
        ),
    }.get
    return store


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    # Mock for Anthropic-style client (default in ContentValidator)
    client.messages.create.return_value.content = [
        MagicMock(
            text=json.dumps(
                {
                    "question_coverage": [
                        {
                            "question": "What are microplastics?",
                            "addressed": "FULLY_ADDRESSED",
                            "justification": "",
                        }
                    ],
                    "style_issues": [],
                }
            )
        )
    ]
    return client


@pytest.fixture
def validation_module(mock_claim_store, mock_llm_client):
    return ValidationModule(
        claim_store=mock_claim_store, llm_client=mock_llm_client, model="test-model"
    )


def create_section(
    content: str,
    section_id: int = 1,
    title: str = "Test Section",
    word_count: int = 1200,
) -> Section:
    citations = []
    # Extract citations from content for the Section object
    for match in re.finditer(r'[(.*?):\s*"(.*?)"]', content):
        citations.append(
            Citation(
                claim_id=match.group(1).strip(),
                quoted_text=match.group(2).strip(),
                location_in_section=match.start(),
            )
        )

    return Section(
        section_id=section_id,
        title=title,
        content=content,
        citations=citations,
        word_count=word_count,
        created_at=datetime.datetime.now(datetime.UTC).isoformat(),
    )


# Test cases for CitationValidator
def test_citation_valid_perfect_match(mock_claim_store):
    validator = CitationValidator(mock_claim_store)
    content = 'This is some text [claim_001: "Fish populations declined 40% in coastal regions due to microplastics."].'
    section = create_section(content)
    issues = validator.validate(section)
    assert not issues


def test_citation_invalid_claim_id(mock_claim_store):
    validator = CitationValidator(mock_claim_store)
    content = 'Some text [non_existent_claim: "Some quote"] here.'
    section = create_section(content)
    issues = validator.validate(section)
    assert len(issues) == 1
    assert issues[0].issue_type == IssueType.CITATION_MISSING
    assert issues[0].severity == Severity.CRITICAL


def test_citation_quote_mismatch_critical(mock_claim_store):
    validator = CitationValidator(mock_claim_store)
    content = (
        'Text with a bad quote [claim_001: "Fish populations declined significantly."].'
    )
    section = create_section(content)
    issues = validator.validate(section)
    assert len(issues) == 1
    assert issues[0].issue_type == IssueType.CITATION_QUOTE_MISMATCH
    assert issues[0].severity == Severity.CRITICAL


def test_citation_invalid_format(mock_claim_store):
    validator = CitationValidator(mock_claim_store)
    content = "Bad format [claim_001: Some quote here]."
    section = create_section(content)
    issues = validator.validate(section)
    assert len(issues) >= 1  # Depending on regex, might catch multiple aspects
    assert any(
        i.issue_type == IssueType.CITATION_INVALID and i.severity == Severity.CRITICAL
        for i in issues
    )


# Test cases for ContentValidator (LLM-based)
def test_content_validator_questions_fully_addressed(mock_llm_client):
    validator = ContentValidator(mock_llm_client, "test-model")
    section = create_section(
        "Microplastics are small plastic pieces less than 5mm long."
    )
    questions = ["What are microplastics?"]
    issues = validator.validate(section, questions)
    assert not issues  # LLM mock returns no issues


def test_content_validator_questions_not_addressed(mock_llm_client):
    # Configure mock LLM to return NOT_ADDRESSED
    mock_llm_client.messages.create.return_value.content = [
        MagicMock(
            text=json.dumps(
                {
                    "question_coverage": [
                        {
                            "question": "What are microplastics?",
                            "addressed": "NOT_ADDRESSED",
                            "justification": "",
                        }
                    ],
                    "style_issues": [],
                }
            )
        )
    ]
    validator = ContentValidator(mock_llm_client, "test-model")
    section = create_section("This section is empty.")
    questions = ["What are microplastics?"]
    issues = validator.validate(section, questions)
    assert len(issues) == 1
    assert issues[0].issue_type == IssueType.QUESTION_NOT_ANSWERED
    assert issues[0].severity == Severity.CRITICAL


def test_content_validator_style_issue(mock_llm_client):
    # Configure mock LLM to return a style issue
    mock_llm_client.messages.create.return_value.content = [
        MagicMock(
            text=json.dumps(
                {
                    "question_coverage": [
                        {
                            "question": "What are microplastics?",
                            "addressed": "FULLY_ADDRESSED",
                            "justification": "",
                        }
                    ],
                    "style_issues": [
                        {
                            "issue_type": "STYLE_MISMATCH",
                            "severity": "WARNING",
                            "message": "Tone is too informal.",
                            "suggestion": "Use academic language.",
                        }
                    ],
                }
            )
        )
    ]
    validator = ContentValidator(mock_llm_client, "test-model")
    section = create_section("Hey, this paper is cool!")
    questions = ["What are microplastics?"]
    issues = validator.validate(section, questions)
    assert len(issues) == 1
    assert issues[0].issue_type == IssueType.STYLE_MISMATCH
    assert issues[0].severity == Severity.WARNING


# Test cases for ValidationModule orchestrator
def test_validation_module_critical_citation_halts(validation_module, mock_claim_store):
    # Ensure mock_claim_store returns None for a specific claim_id to simulate missing claim
    mock_claim_store.get.side_effect = lambda cid: {
        "claim_001": Claim(
            claim_id="claim_001",
            source_id="source_1",
            statement="Fish populations declined 40% in coastal regions due to microplastics.",
            context="A study conducted over 5 years",
            evidence_type=EvidenceType.EMPIRICAL_FINDING,
            tags=[],
            page_number=1,
            section_in_source="Results",
        ),
        "non_existent_claim": None,
    }.get(cid)

    content = 'This section cites a missing claim [non_existent_claim: "Some irrelevant quote"] and then has more content.'
    section = create_section(content)
    questions = ["Any question"]

    result = validation_module.validate_section(section, questions)

    assert not result.passed
    assert any(
        i.issue_type == IssueType.CITATION_MISSING and i.severity == Severity.CRITICAL
        for i in result.issues
    )
    # Should only have citation issues, not content/style issues if early exit works
    assert not any(
        i.issue_type == IssueType.QUESTION_NOT_ANSWERED for i in result.issues
    )


def test_validation_module_all_passed(validation_module):
    content = 'This is a well-written section with a correct citation [claim_001: "Fish populations declined 40% in coastal regions due to microplastics."].'
    section = create_section(content)
    questions = ["What are microplastics?"]
    result = validation_module.validate_section(section, questions)
    assert result.passed
    assert not result.issues


def test_validation_module_word_count_warning(validation_module):
    content = "Short content. " * 50  # 100 words
    section = create_section(content, word_count=100)
    questions = ["What are microplastics?"]
    result = validation_module.validate_section(section, questions)
    assert result.passed  # Word count is only WARNING
    assert any(i.issue_type == IssueType.WORD_COUNT for i in result.issues)


def test_citation_quote_mismatch_with_punctuation_and_case_differences(
    mock_claim_store,
):
    validator = CitationValidator(mock_claim_store)
    content = 'The study states [claim_001: "fish populations declined 40% in coastal regions, due to microplastics."].'
    section = create_section(content)
    issues = validator.validate(section)
    assert not issues, f"Expected no issues, but got: {issues}"

    content_different_case = 'The study states [claim_001: "FISH POPULATIONS DECLINED 40% IN COASTAL REGIONS DUE TO MICROPLASTICS."].'
    section_different_case = create_section(content_different_case)
    issues_different_case = validator.validate(section_different_case)
    assert not issues_different_case, (
        f"Expected no issues for different case, but got: {issues_different_case}"
    )

    content_subtle_change = 'The study states [claim_001: "Fish populations declined 40% in coastal regions, owing to microplastics."].'
    section_subtle_change = create_section(content_subtle_change)
    issues_subtle_change = validator.validate(section_subtle_change)
    assert len(issues_subtle_change) == 1
    assert issues_subtle_change[0].issue_type == IssueType.CITATION_QUOTE_MISMATCH
    assert issues_subtle_change[0].severity == Severity.CRITICAL
