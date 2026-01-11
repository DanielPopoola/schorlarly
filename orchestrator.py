import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from agents.input_validator import InputValidator
from agents.research_agent import ResearchAgent
from agents.writing_agent import WritingAgent
from config.settings import settings
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

	def initialize(self, input_data: dict[str, Any]) -> None:
		logger.info('Initializing orchestrator...')
		config = self.validator.validate(input_data)
		logger.info(f'✓ Input validated. Topic: {config["topic"][:50]}...')

		state = {
			'config': config,
			'current_section_id': 0,
			'completed_sections': [],
			'failed_sections': [],
			'research_complete': False,
			'created_at': datetime.now(UTC).isoformat(),
			'updated_at': datetime.now(UTC).isoformat(),
		}
		self._save_state(state)
		logger.info(f'✓ State initialized at {self.state_file}')

		sections = [
			{
				'id': idx,
				'title': title,
				'objective': self._generate_objective(title),
				'status': 'pending',
				'word_count': 0,
				'citations_count': 0,
			}
			for idx, title in enumerate(config['template'])
		]

		plan = {
			'topic': config['topic'],
			'sections': sections,
			'total_sections': len(sections),
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

			self._process_section(section, state, plan)

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

	def _process_section(self, section: dict, state: dict, plan: dict) -> None:
		section_id = section['id']
		section_title = section['title']

		logger.info(f'\n[Section {section_id}] Processing: {section_title}')
		state['current_section_id'] = section_id
		self._save_state(state)

		available_sources = [self.research_agent.get_source(sid) for sid in plan.get('global_source_ids', [])]
		available_sources = [s for s in available_sources if s]

		previous_content = self._load_section_content(section_id - 1) if section_id > 0 else None

		try:
			logger.info(f'  Writing with {len(available_sources)} available sources...')
			result = self._writing_agent.write_section(  # type: ignore
				section_title=section_title,
				section_objective=section['objective'],
				topic=state['config']['topic'],
				available_sources=available_sources,
				style_preferences=state['config']['style'],
				constraints=state['config']['constraints'],
				previous_section_text=previous_content,
			)

			self._save_section_content(section_id, section_title, result['content'])

			section['status'] = 'drafted'
			section['word_count'] = result['word_count']
			section['citations_count'] = len(result['citations_used'])
			self._save_plan(plan)

		except Exception as e:
			logger.error(f'  ✗ Writing failed: {e}')
			section['status'] = 'failed'
			state['failed_sections'].append(section_id)
			self._save_plan(plan)
			self._save_state(state)

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

	def _generate_objective(self, title: str) -> str:
		title_lower = title.lower()
		objectives = {
			'introduction': 'Introduce the topic, provide background, and state research objectives',
			'literature': 'Review existing research and identify gaps',
			'review': 'Review existing research and identify gaps',
			'methodology': 'Describe research methods and approach',
			'method': 'Describe research methods and approach',
			'result': 'Present research findings and analysis',
			'finding': 'Present research findings and analysis',
			'discussion': 'Interpret findings and discuss implications',
			'conclusion': 'Summarize findings and suggest future work',
		}

		for key, objective in objectives.items():
			if key in title_lower:
				return objective

		return f'Address the requirements of the {title} section'

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
