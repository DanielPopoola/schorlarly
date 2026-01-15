import logging
from pathlib import Path

from src.core.config_loader import SectionConfig, get_config
from src.core.context_manager import ContextManager, SectionContext
from src.core.state_manager import SectionStatus, StateManager
from src.llm.client import create_llm_client_from_config
from src.parsers.input_parser import InputParser, ProjectInput

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Orchestrator:
	def __init__(self, project_name: str):
		self.project_name = project_name
		self.project_input: ProjectInput | None = None
		self.config = get_config()

		output_config = self.config.get_output_config()
		state_dir = Path(output_config['state_dir'])

		self.state_manager = StateManager(project_name, state_dir)

		context_file = state_dir / f'{project_name}_context.json'
		self.context_manager = ContextManager(context_file)
		self.context_manager.load_state()

		self.sections = self.config.get_sections()
		section_names = [s.name for s in self.sections]
		self.state_manager.initialize_sections(section_names)

		llm_config = self.config.get_llm_config()
		self.llm_client = create_llm_client_from_config(llm_config)
		self.parser = InputParser(self.llm_client)

		logger.info(f'Orchestrator initialized for project: {project_name}')

	def generate_paper(self):
		logger.info('Starting paper generation...')
		for section_config in self.sections:
			if self.state_manager.get_section_status(section_config.name) == SectionStatus.COMPLETED:
				logger.info(f"Section '{section_config.name}' already completed, skipping")
				continue

			try:
				self._generate_section(section_config)
			except Exception as e:
				logger.error(f"Failed to generate section '{section_config.name}': {e}")
				self.state_manager.set_section_status(section_config.name, SectionStatus.FAILED)
				raise

		if self.state_manager.is_complete():
			logger.info('All sections completed successfully!')
			self._finalize_paper()

	def _generate_section(self, section_config: SectionConfig):
		logger.info(f'Generating section: {section_config.name}')
		self.state_manager.set_section_status(section_config.name, SectionStatus.IN_PROGRESS)

		context = self.context_manager.get_context_for_section(section_config.name, section_config.depends_on)

		if self.project_input:
			input_context = self.parser.get_context_for_section(self.project_input, section_config.type)
			context['input_context'] = input_context

		logger.info(f'  Type: {section_config.type}')
		logger.info(f'  Word count: {section_config.word_count["min"]}-{section_config.word_count["max"]}')
		logger.info(f'  Dependencies: {section_config.depends_on}')
		logger.info(f'  Context includes {len(context["previously_completed"])} previous sections')

		# TODO: Call generator and get section_context back
		# For now, create dummy section context
		section_context = SectionContext(
			name=section_config.name,
			content=f'[Generated content for {section_config.name}]',
			key_points=[f'Point 1 from {section_config.name}', f'Point 2 from {section_config.name}'],
			citations=[],
			word_count=500,
			terms_defined=[],
		)

		# Add to context manager
		self.context_manager.add_section(section_context)

		# Mark as complete
		self.state_manager.set_section_status(section_config.name, SectionStatus.COMPLETED)
		logger.info(f'✓ Completed: {section_config.name}')

		# Show progress
		progress = self.state_manager.get_progress()
		logger.info(
			f'Progress: {progress["completed"]}/{progress["total_sections"]} sections '
			f'({progress["progress_percentage"]:.1f}%)'
		)

	def _finalize_paper(self):
		logger.info('Finalizing paper...')

		# TODO: Implement actual finalization
		# - Combine all sections
		# - Export to Word
		# - Generate summary report

		logger.info('✓ Paper generation complete!')

	def load_input(self, input_file: Path):
		logger.info(f'Loading input from: {input_file}')
		self.project_input = self.parser.parse_file(input_file)
		logger.info(f'Input loaded successfully: {self.project_input.title}')

	def get_progress(self):
		return self.state_manager.get_progress()

	def resume(self):
		logger.info('Resuming paper generation...')
		self.generate_paper()

	def reset(self):
		logger.warning('Resetting all progress...')
		self.state_manager.reset()
		self.context_manager.clear()
		logger.info('Reset complete. Ready to start fresh.')
