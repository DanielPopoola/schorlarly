import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agents.input_validator import InputValidator
from utils.logger import logger


class Orchestrator:
	def __init__(self, state_dir: Path | str = 'state'):
		self.state_dir = Path(state_dir)
		self.state_dir.mkdir(parents=True, exist_ok=True)

		self.state_file = self.state_dir / 'state.json'
		self.plan_file = self.state_dir / 'plan.json'

		self.validator = InputValidator()

	def initialize(self, input_data: dict[str, Any]) -> None:
		logger.info('Initializing orchestrator...')

		config = self.validator.validate(input_data)
		logger.info(f'✓ Input validated. Topic: {config["topic"][:50]}...')

		state = self._create_initial_state(config)
		self._save_state(state)
		logger.info(f'✓ State initialized at {self.state_file}')

		plan = self._create_plan(config)
		self._save_plan(plan)
		logger.info(f'✓ Plan created with {len(plan["sections"])} sections')

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

		for section in plan['sections']:
			section_id = section['id']
			section_title = section['title']

			if section_id in state['completed_sections']:
				logger.info(f'[Section {section_id}] {section_title} - ALREADY COMPLETED')
				continue

			logger.info(f'\n[Section {section_id}] Processing: {section_title}')

			logger.info(f"  TODO: Research sources for '{section_title}'")
			logger.info('  TODO: Write section content')
			logger.info('  TODO: Validate citations')
			logger.info('  → This section will be implemented in Phase 2-4')

			state['current_section_id'] = section_id
			self._save_state(state)

		logger.info(f'\n{"=" * 60}')
		logger.info('Phase 1 complete! State and plan files created.')
		logger.info(f'State file: {self.state_file}')
		logger.info(f'Plan file: {self.plan_file}')
		logger.info(f'{"=" * 60}\n')

	def _create_initial_state(self, config: dict) -> dict:
		"""Create the initial state object."""
		return {
			'config': config,
			'current_section_id': 0,
			'completed_sections': [],
			'failed_sections': [],
			'thesis': None,
			'created_at': datetime.now(UTC).isoformat(),
			'updated_at': datetime.now(UTC).isoformat(),
		}

	def _create_plan(self, config: dict) -> dict:
		sections = []

		for idx, title in enumerate(config['template']):
			sections.append(
				{
					'id': idx,
					'title': title,
					'objective': self._generate_section_objective(title),
					'status': 'pending',
				}
			)

		return {
			'topic': config['topic'],
			'sections': sections,
			'total_sections': len(sections),
			'created_at': datetime.now(UTC).isoformat(),
		}

	def _generate_section_objective(self, title: str) -> str:
		title_lower = title.lower()

		if 'introduction' in title_lower:
			return 'Introduce the topic, provide background, and state research objectives'
		elif 'literature' in title_lower or 'review' in title_lower:
			return 'Review existing research and identify gaps'
		elif 'methodology' in title_lower or 'method' in title_lower:
			return 'Describe research methods and approach'
		elif 'result' in title_lower or 'finding' in title_lower:
			return 'Present research findings and analysis'
		elif 'discussion' in title_lower:
			return 'Interpret findings and discuss implications'
		elif 'conclusion' in title_lower:
			return 'Summarize findings and suggest future work'
		else:
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
			logger.info(f'    Objective: {section["objective"]}')
			logger.info(f'    Status: {section["status"]}\n')

		logger.info(f'{"=" * 60}\n')


# Example usage
if __name__ == '__main__':
	# Example input
	input_data = {
		'topic': 'Impact of microplastics on marine biodiversity',
		'template': [
			'Introduction',
			'Literature Review',
			'Methodology',
			'Findings',
			'Discussion',
			'Conclusion',
		],
		'style': {
			'tone': 'formal',
			'citation_format': 'Harvard',
		},
	}

	orchestrator = Orchestrator(state_dir='state')
	orchestrator.initialize(input_data)
	orchestrator.run()
