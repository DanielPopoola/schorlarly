import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from agents.context_manager import ContextManager
from agents.input_validator import InputValidator
from agents.research_agent import ResearchAgent
from agents.source_filter import SourceFilter
from agents.validation_agent import CitationValidator
from agents.writing_agent import WritingAgent
from config.settings import settings
from models import Finding, Severity
from models.template_profile import SectionProfile, SectionType, TemplateProfileManager
from utils.llm_client import UnifiedLLMClient
from utils.logger import logger


class Orchestrator:
	def __init__(self, state_dir: Path | str = 'state'):
		self.state_dir = Path(state_dir)
		self.state_dir.mkdir(parents=True, exist_ok=True)
		self.state_file = self.state_dir / 'state.json'
		self.plan_file = self.state_dir / 'plan.json'
		self.sections_dir = self.state_dir / 'sections'
		self.sections_dir.mkdir(parents=True, exist_ok=True)

		self.validator = InputValidator()
		self.research_agent = ResearchAgent(
			storage_dir=self.state_dir / 'sources',
			max_papers_per_section=10,
		)
		self._writing_agent = None
		self.llm_client: UnifiedLLMClient = UnifiedLLMClient(
			client=OpenAI(base_url='https://openrouter.ai/api/v1', api_key=settings.OPENROUTER_API_KEY),
			model='xiaomi/mimo-v2-flash:free',
			site_url='https://github.com/DanielPopoola/scholarly',
			app_name='Scholarly',
		)
		self.context_manager = ContextManager(self.llm_client)
		self.profile_manager = TemplateProfileManager()
		self.current_profile = None

	def initialize(self, input_data: dict[str, Any]) -> None:
		logger.info('Initializing orchestrator...')
		config = self.validator.validate(input_data)
		logger.info(f'✓ Input validated. Topic: {config["topic"][:50]}...')

		self.current_profile = self.profile_manager.detect_profile(template=config['template'], topic=config['topic'])
		logger.info(f'✓ Detected template profile: {self.current_profile.name}')

		state = {
			'config': config,
			'profile_name': self.current_profile.name,
			'current_section_id': 0,
			'completed_sections': [],
			'failed_sections': [],
			'research_complete': False,
			'created_at': datetime.now(UTC).isoformat(),
			'updated_at': datetime.now(UTC).isoformat(),
		}
		self._save_state(state)
		logger.info(f'✓ State initialized at {self.state_file}')

		sections = []
		for idx, title in enumerate(config['template']):
			section_profile = self.current_profile.get_section_profile(title)

			sections.append(
				{
					'id': idx,
					'title': title,
					'objective': self._generate_objective(title, section_profile),
					'status': 'pending',
					'word_count': 0,
					'citations_count': 0,
					'min_citations': section_profile.min_citations,
					'max_words': section_profile.max_word_count,
					'section_type': section_profile.section_type.value,
					'requires_code': section_profile.requires_code,
					'requires_diagrams': section_profile.requires_diagrams,
					'research_strategy': section_profile.research_strategy,
				}
			)

		plan = {
			'topic': config['topic'],
			'sections': sections,
			'total_sections': len(sections),
			'profile': self.current_profile.name,
			'created_at': datetime.now(UTC).isoformat(),
		}
		self._save_plan(plan)
		logger.info(f'✓ Plan created with {len(sections)} sections')
		self._log_plan(plan)

	def run(self) -> None:
		if not self.state_file.exists():
			raise RuntimeError('State not initialized. Call initialize() first.')

		state = self._load_state()
		plan = self._load_plan()

		logger.info(f'\n{"=" * 60}')
		logger.info('Starting paper generation...')
		logger.info(f'Topic: {state["config"]["topic"]}')
		logger.info(f'Sections: {len(plan["sections"])}')
		logger.info(f'{"=" * 60}\n')

		if not state['research_complete']:
			self._run_global_research(state, plan)

		if self._writing_agent is None:
			self._writing_agent = self._init_writing_agent()

		for section in plan['sections']:
			if section['status'] in ['validated', 'failed']:
				logger.info(f'[Section {section["id"]}] {section["title"]} - {section["status"].upper()}')
				continue

			self._process_section_with_gap_detection(section, state, plan)

		logger.info(f'\n{"=" * 60}')
		logger.info('Paper generation complete!')
		validated = sum(1 for s in plan['sections'] if s['status'] == 'validated')
		drafted = sum(1 for s in plan['sections'] if s['status'] == 'drafted')
		failed = sum(1 for s in plan['sections'] if s['status'] == 'failed')
		logger.info(f'Validated: {validated}, Drafted: {drafted}, Failed: {failed}')
		logger.info(f'{"=" * 60}\n')

	def _run_global_research(self, state: dict, plan: dict) -> None:
		logger.info(f'\n{"=" * 60}')
		logger.info('PHASE 2: GLOBAL RESEARCH')
		logger.info(f'{"=" * 60}\n')
		logger.info('Conducting research once for entire paper...')

		source_ids = self.research_agent.research_section(
			topic=state['config']['topic'],
			section_title='全体',
			section_objective='Comprehensive research for entire paper',
		)

		plan['global_source_ids'] = source_ids
		state['research_complete'] = True
		self._save_plan(plan)
		self._save_state(state)

		logger.info(f'✓ Global research complete: {len(source_ids)} sources')
		logger.info(f'{"=" * 60}\n')

	def _init_writing_agent(self) -> WritingAgent:
		import os

		if settings.OPENROUTER_API_KEY or os.getenv('OPENROUTER_API_KEY'):
			api_key = settings.OPENROUTER_API_KEY or os.getenv('OPENROUTER_API_KEY')
			raw_client = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=api_key)
			llm_client = UnifiedLLMClient(
				client=raw_client,
				model='xiaomi/mimo-v2-flash:free',
				site_url='https://github.com/DanielPopoola/scholarly',
				app_name='Scholarly',
			)
			logger.info('✓ Writing agent initialized with OpenRouter')
		elif settings.OPENAI_API_KEY:
			from openai import OpenAI as OpenAIClient

			raw_client = OpenAIClient(api_key=settings.OPENAI_API_KEY)
			llm_client = UnifiedLLMClient(client=raw_client, model='gpt-4o-mini')
			logger.info('✓ Writing agent initialized with OpenAI')
		elif settings.ANTHROPIC_API_KEY:
			from anthropic import Anthropic

			raw_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
			llm_client = UnifiedLLMClient(client=raw_client, model='claude-3-5-sonnet-20241022')
			logger.info('✓ Writing agent initialized with Anthropic')
		else:
			raise RuntimeError('No LLM API key found!')

		return WritingAgent(llm_client=llm_client)

	def _generate_objective(self, title: str, profile: SectionProfile) -> str:
		"""Generate objectives tailored to section type"""

		objectives = {
			SectionType.INTRO_CONCLUSION: {
				'introduction': 'Introduce the research problem, establish context, and state objectives',
				'background': 'Provide comprehensive background on the domain and establish research context',
				'statement': 'Clearly define the research problem and its significance',
				'objective': 'State specific, measurable objectives of the study',
				'significance': 'Justify the importance and potential impact of the research',
				'scope': 'Define boundaries and limitations of the study',
				'summary': 'Recapitulate key findings and their implications',
				'conclusion': 'Synthesize findings and state final conclusions',
				'recommendations': 'Provide actionable recommendations based on findings',
			},
			SectionType.RESEARCH_LITERATURE: {
				'literature': 'Review and synthesize existing research, identify gaps',
				'existing': 'Analyze existing approaches and their limitations',
				'efforts': 'Evaluate prior attempts to address the problem',
			},
			SectionType.METHODOLOGY: {
				'methodology': 'Describe research methods, procedures, and justification',
				'approach': 'Detail the specific approach and rationale',
			},
			SectionType.TECHNICAL_ANALYSIS: {
				'analysis': 'Analyze system requirements and constraints',
				'design': 'Present system architecture and design decisions',
				'flowchart': 'Illustrate process flows and system logic',
			},
			SectionType.IMPLEMENTATION: {
				'implementation': 'Document implementation details and technical choices',
				'test': 'Describe testing procedures and results',
				'documentation': 'Provide technical and user documentation',
				'maintenance': 'Outline maintenance procedures and support',
			},
			SectionType.DISCUSSION: {
				'findings': 'Present and analyze research findings',
				'discussion': 'Interpret results and discuss implications',
				'results': 'Report research outcomes with supporting evidence',
			},
		}

		title_lower = title.lower()
		section_objectives = objectives.get(profile.section_type, {})

		for keyword, objective in section_objectives.items():
			if keyword in title_lower:
				return objective

		return f'Address the requirements of the {title} section'

	def _refine_objective(
		self, section_title: str, initial_objective: str, topic: str, prior_findings: list[Finding]
	) -> str:
		if not prior_findings:
			return initial_objective

		findings_text = '\n'.join(f'- {f.text}' for f in prior_findings)

		prompt = f"""You are planning an academic paper section.

# Paper Topic
{topic}

# Section to Write
{section_title}

# Initial Objective (Generic)
{initial_objective}

# Key Findings from Prior Sections
{findings_text}

# Task
Refine the objective for "{section_title}" to build upon these specific findings.
Make it concrete and actionable for the writer.

Output only the refined objective (1-2 sentences)."""

		refined = self.llm_client.generate(prompt, max_tokens=200).strip()
		logger.info(f'  Objective refined: {initial_objective} → {refined}')
		return refined

	def _process_section_with_gap_detection(self, section: dict, state: dict, plan: dict) -> None:
		section_id = section['id']
		section_title = section['title']

		if section_id > 0:
			intro_findings = self.context_manager.extract_findings_for_refinement(0)
			if intro_findings:
				refined_objective = self._refine_objective(
					section_title=section_title,
					initial_objective=section['objective'],
					topic=state['config']['topic'],
					prior_findings=intro_findings,
				)
				section['objective'] = refined_objective
				self._save_plan(plan)

		min_citations = section.get('min_citations', 3)
		max_words = section.get('max_words', 1500)
		section_type = section.get('section_type', 'discussion')

		logger.info(f'\n[Section {section_id}] Type: {section_type}, Citations: {min_citations}+, Words: {max_words}')

		# Check if this section needs code/diagrams
		if section.get('requires_code'):
			logger.warning('Section requires code examples (not yet implemented)')
		if section.get('requires_diagrams'):
			logger.warning('Section requires diagrams (not yet implemented)')

		all_sources = [self.research_agent.get_source(sid) for sid in plan.get('global_source_ids', [])]
		all_sources = [s for s in all_sources if s]

		if section.get('research_strategy') == 'targeted':
			source_filter = SourceFilter()
			relevant_sources = source_filter.filter_by_relevance(
				sources=all_sources, objective=section['objective'], min_score=0.3, top_k=8
			)
			logger.info(f'  Filtered {len(all_sources)} → {len(relevant_sources)} (targeted strategy)')
		else:
			source_filter = SourceFilter()
			relevant_sources = source_filter.filter_by_relevance(
				sources=all_sources, objective=section['objective'], min_score=0.2, top_k=4
			)
			logger.info(f'  Filtered {len(all_sources)} → {len(relevant_sources)} (global strategy)')

		max_retries = 3
		for attempt in range(1, max_retries + 1):
			try:
				result = self._writing_agent.write_section(  # type: ignore
					section_title=section_title,
					section_objective=section['objective'],
					topic=state['config']['topic'],
					available_sources=relevant_sources,
					style_preferences=state['config']['style'],
					constraints={'max_section_word_count': max_words, 'min_citations_per_section': min_citations},
					previous_section_text=self._load_section_content(section_id - 1) if section_id > 0 else None,
				)

				validator = CitationValidator(self.research_agent.sources_db)
				validation = validator.validate_section(
					section_id=section_id, content=result['content'], min_citations=min_citations, max_words=max_words
				)

				if validation.passed:
					self._save_section_content(section_id, section_title, result['content'])
					section['status'] = 'validated'
					section['word_count'] = result['word_count']
					section['citations_count'] = len(result['citations_used'])
					self._save_plan(plan)
					logger.info(f'  ✓ Section validated (attempt {attempt})')
					return

				critical_issues = [i for i in validation.issues if i.severity == Severity.CRITICAL]
				if critical_issues and hasattr(validation, 'missing_topics') and validation.missing_topics:
					logger.warning(f'  Gap detected: {validation.missing_topics}')
					gap_query = f'{state["config"]["topic"]} {" ".join(validation.missing_topics)}'
					new_source_ids = self.research_agent.research_section(
						topic=gap_query, section_title=section_title, section_objective=section['objective']
					)
					new_sources = [self.research_agent.get_source(sid) for sid in new_source_ids]
					relevant_sources.extend([s for s in new_sources if s])
					logger.info(f'  Added {len(new_sources)} gap-filling sources, retrying...')
				else:
					logger.warning(f'  Validation failed (attempt {attempt})')

			except Exception as e:
				logger.error(f'  Writing failed (attempt {attempt}): {e}')

		section['status'] = 'failed'
		state['failed_sections'].append(section_id)
		self._save_plan(plan)
		self._save_state(state)
		logger.error(f'  ✗ Section failed after {max_retries} attempts')

	def _save_state(self, state: dict) -> None:
		state['updated_at'] = datetime.now(UTC).isoformat()
		with open(self.state_file, 'w') as f:
			json.dump(state, f, indent=2)

	def _load_state(self) -> dict:
		with open(self.state_file) as f:
			return json.load(f)

	def _save_plan(self, plan: dict) -> None:
		with open(self.plan_file, 'w') as f:
			json.dump(plan, f, indent=2)

	def _load_plan(self) -> dict:
		with open(self.plan_file) as f:
			return json.load(f)

	def _log_plan(self, plan: dict) -> None:
		logger.info(f'\n{"=" * 60}')
		logger.info('EXECUTION PLAN')
		logger.info(f'{"=" * 60}')
		logger.info(f'Topic: {plan["topic"]}')
		logger.info(f'Total sections: {plan["total_sections"]}\n')
		for section in plan['sections']:
			logger.info(f'[{section["id"]}] {section["title"]}')
			logger.info(f'    Objective: {section["objective"]}\n')
		logger.info(f'{"=" * 60}\n')

	def _save_section_content(self, section_id: int, section_title: str, content: str) -> None:
		filename = f'{section_id:02d}_{section_title.lower().replace(" ", "_")}.md'
		filepath = self.sections_dir / filename
		with open(filepath, 'w') as f:
			f.write(f'# {section_title}\n\n{content}')

	def _load_section_content(self, section_id: int) -> str | None:
		files = list(self.sections_dir.glob(f'{section_id:02d}_*.md'))
		if not files:
			return None
		with open(files[0]) as f:
			lines = f.readlines()
			return ''.join(lines[2:]) if len(lines) > 2 else None


if __name__ == '__main__':
	input_data = {
		'topic': 'transformer neural networks',
		'template': ['Introduction', 'Methodology'],
	}

	orchestrator = Orchestrator(state_dir='state')
	orchestrator.initialize(input_data)
	orchestrator.run()
