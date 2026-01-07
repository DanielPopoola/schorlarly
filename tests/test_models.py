import pytest
from datetime import datetime, UTC
from src.models import (
	Section,
	Citation,
	Claim,
	Finding,
	SectionSummary,
	SectionStatus,
	EvidenceType,
	ValidationIssue,
	ValidationResult,
	IssueType,
	Severity,
	SearchResult,
	CitationReference,
	Question,
	ResearchPlan,
	GlobalState,
)


def test_claim_creation():
	claim = Claim(
		claim_id='test_001',
		source_id='arxiv:2301.12345',
		statement='Fish populations declined 40%',
		context='5-year study',
		evidence_type=EvidenceType.EMPIRICAL_FINDING,
		tags=['fish', 'decline'],
		page_number=5,
		section_in_source='Results',
	)

	assert claim.claim_id == 'test_001'
	assert claim.evidence_type == EvidenceType.EMPIRICAL_FINDING
	assert len(claim.tags) == 2


def test_section_creation():
	citations = [
		Citation(
			claim_id='claim_001',
			quoted_text='Fish declined 40%',
			location_in_section=123,
		)
	]

	section = Section(
		section_id=1,
		title='Introduction',
		content='This is the introduction text...',
		citations=citations,
		word_count=100,
		status=SectionStatus.DRAFT,
		created_at=datetime.now(UTC).isoformat(),
	)

	assert section.section_id == 1
	assert len(section.citations) == 1
	assert section.status == SectionStatus.DRAFT


def test_validation_issue_creation():
	issue = ValidationIssue(
		issue_type=IssueType.CITATION_MISSING,
		severity=Severity.CRITICAL,
		message="Claim ID 'xyz' not found",
		suggestion='Use valid claim ID',
		location='line 45',
	)

	assert issue.severity == Severity.CRITICAL
	assert 'not found' in issue.message


def test_validation_result():
	issues = [
		ValidationIssue(
			issue_type=IssueType.WORD_COUNT,
			severity=Severity.WARNING,
			message='Section too short',
			suggestion='Add more content',
			location=None,
		)
	]

	result = ValidationResult(
		validation_id='val_001',
		section_id=1,
		passed=False,
		issues=issues,
		attempt=1,
		timestamp=datetime.now(UTC).isoformat(),
	)

	assert not result.passed
	assert len(result.issues) == 1


def test_citation_reference_creation():
	doi_ref = CitationReference(
		identifier='10.1038/s41586-023-12345-6',
		identifier_type='doi',
		metadata={'provider': 'semantic_scholar'},
	)
	assert doi_ref.identifier_type == 'doi'

	url_ref = CitationReference(
		identifier='https://arxiv.org/abs/2301.12345',
		identifier_type='url',
		metadata={'provider': 'perplexity'},
	)
	assert url_ref.identifier_type == 'url'


def test_search_result_creation():
	citations = [
		CitationReference(
			identifier='paper_123',
			identifier_type='semantic_scholar_id',
			metadata=None,
		)
	]

	result = SearchResult(
		source_id='arxiv:2301.12345',
		title='Test Paper',
		content='Abstract content',
		authors=['Dr. Smith', 'Dr. Jones'],
		year=2023,
		url='https://arxiv.org/abs/2301.12345',
		citations=citations,
		metadata={'provider': 'arxiv'},
	)

	assert result.source_id == 'arxiv:2301.12345'
	assert len(result.citations) == 1
	assert result.year == 2023


def test_question_creation():
	question = Question(
		question_id='q_001',
		text='What are the impacts of microplastics?',
		target_sections=[2, 3],
	)

	assert len(question.target_sections) == 2
	assert 2 in question.target_sections


def test_research_plan_creation():
	"""Test creating a complete ResearchPlan"""
	questions = [
		Question(
			question_id='q_001',
			text='Question 1',
			target_sections=[1],
		)
	]

	plan = ResearchPlan(
		topic='Microplastics',
		questions=questions,
		total_sources=10,
		completed_at=datetime.now(UTC).isoformat(),
	)

	assert plan.topic == 'Microplastics'
	assert len(plan.questions) == 1
	assert plan.total_sources == 10


# ============================================================================
# State Model Tests
# ============================================================================


def test_global_state_initialization():
	"""Test creating an empty GlobalState"""
	state = GlobalState(
		thesis='Microplastics harm marine life',
		key_terms={},
		section_summaries=[],
		decisions_made=[],
		current_section_id=0,
		total_tokens_used=0,
		cost_usd=0.0,
		retry_counts={},
	)

	assert state.thesis == 'Microplastics harm marine life'
	assert len(state.section_summaries) == 0
	assert state.current_section_id == 0


def test_global_state_retry_tracking():
	"""Test retry count tracking methods"""
	state = GlobalState(
		thesis='Test',
		current_section_id=1,
	)

	# Initially no retries
	assert state.get_retry_count(1) == 0

	# Record some retries
	state.record_retry(1)
	state.record_retry(1)
	assert state.get_retry_count(1) == 2

	# Different section
	state.record_retry(2)
	assert state.get_retry_count(2) == 1
	assert state.get_retry_count(1) == 2  # Should be unchanged


def test_global_state_decision_tracking():
	"""Test decision audit trail"""
	state = GlobalState(
		thesis='Test',
		current_section_id=3,
	)

	state.add_decision('Chose narrow focus')
	state.add_decision('Added counterargument')

	assert len(state.decisions_made) == 2
	assert '[Section 3]' in state.decisions_made[0]
	assert 'narrow focus' in state.decisions_made[0]


def test_global_state_with_summaries():
	"""Test adding SectionSummaries to GlobalState"""
	summary = SectionSummary(
		section_id=1,
		section_title='Introduction',
		summary='This section introduces...',
		key_findings=[],
		key_terms=['microplastic', 'bioaccumulation'],
	)

	state = GlobalState(
		thesis='Test',
		section_summaries=[summary],
	)

	assert len(state.section_summaries) == 1
	assert state.section_summaries[0].section_id == 1


def test_global_state_key_terms():
	"""Test key terms dictionary"""
	state = GlobalState(
		thesis='Test',
		key_terms={
			'microplastic': 'Plastic particles less than 5mm',
			'bioaccumulation': 'Buildup in organisms over time',
		},
	)

	assert len(state.key_terms) == 2
	assert '5mm' in state.key_terms['microplastic']


# ============================================================================
# Integration Tests
# ============================================================================


def test_complete_section_workflow():
	"""Test a realistic workflow: draft -> validate -> update state"""
	# 1. Create a draft section
	section = Section(
		section_id=1,
		title='Introduction',
		content="Microplastics are a problem. [claim_001: 'Fish declined 40%']",
		citations=[
			Citation(
				claim_id='claim_001',
				quoted_text='Fish declined 40%',
				location_in_section=50,
			)
		],
		word_count=120,
		status=SectionStatus.DRAFT,
		created_at=datetime.now(UTC).isoformat(),
	)

	# 2. Validate it (simulated pass)
	validation = ValidationResult(
		validation_id='val_001',
		section_id=section.section_id,
		passed=True,
		issues=[],
		attempt=1,
		timestamp=datetime.now(UTC).isoformat(),
	)

	# 3. Create ledger entry
	summary = SectionSummary(
		section_id=section.section_id,
		section_title=section.title,
		summary='Introduces the microplastics problem',
		key_findings=[
			Finding(
				text='Fish populations declining',
				source_ids=['claim_001'],
				section_id=1,
			)
		],
		key_terms=['microplastic'],
	)

	# 4. Update global state
	state = GlobalState(
		thesis='Microplastics harm ecosystems',
		section_summaries=[summary],
		current_section_id=2,  # Moving to next section
	)

	# Verify the workflow
	assert validation.passed
	assert len(state.section_summaries) == 1
	assert state.current_section_id == 2
