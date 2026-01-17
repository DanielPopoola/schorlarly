import logging
import time
from pathlib import Path

from src.core.config_loader import SectionConfig, get_config
from src.core.context_manager import ContextManager
from src.core.state_manager import SectionStatus, StateManager
from src.export.word_exporter import create_word_exporter_from_config
from src.generators import GeneratorFactory
from src.llm.client import create_llm_client_from_config
from src.parsers.input_parser import InputParser, ProjectInput
from src.research import CitationValidator, ResearchSearcher

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

		self.research_searcher = ResearchSearcher(self.config.get_research_config())
		self.citation_validator = CitationValidator(self.llm_client, self.config.get_citation_config())

		generator_config = {'writing': self.config.get_writing_config(), 'citation': self.config.get_citation_config()}

		self.factory = GeneratorFactory(
			self.llm_client, generator_config, self.research_searcher, self.citation_validator
		)

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
		for dep in section_config.depends_on:
			dep_status = self.state_manager.get_section_status(dep)
			if dep_status != SectionStatus.COMPLETED:
				logger.error(f'Cannot generate "{section_config.name}" - dependency "{dep}" not completed')
				raise ValueError(f'Dependency not met: {dep}')

		if self.project_input:
			input_context = self.parser.get_context_for_section(self.project_input, section_config.type)
			context['input_context'] = input_context

		logger.info(f'  Type: {section_config.type}')
		logger.info(f'  Word count: {section_config.word_count["min"]}-{section_config.word_count["max"]}')
		logger.info(f'  Dependencies: {section_config.depends_on}')
		logger.info(f'  Context includes {len(context["previously_completed"])} previous sections')

		generator = self.factory.get_generator(section_config.type)
		logger.info(f'=== Generating: {section_config.name} ===')
		start_time = time.time()
		start_tokens = self.llm_client.get_usage_stats()
		section = generator.generate(section_config, self.project_input, context)
		# Add to context manager
		self.context_manager.add_section(section)
		end_time = time.time()
		end_tokens = self.llm_client.get_usage_stats()

		logger.info(f'Section completed in {end_time - start_time:.2f}s')
		logger.info(
			f'Tokens used: input={end_tokens["input_tokens"] - start_tokens["input_tokens"]}, '
			f'output={end_tokens["output_tokens"] - start_tokens["output_tokens"]}'
		)
		logger.info(f'Total so far: {end_tokens["total_tokens"]} tokens')

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

		exporter = create_word_exporter_from_config(
			self.context_manager,
			{'output': self.config.get_output_config(), 'citation': self.config.get_citation_config()},
		)

		output_path = exporter.export(
			project_name=self.project_name,
			project_title=self.project_input.title if self.project_input else self.project_name,
			author=self.project_input.author if self.project_input else 'Unknown',
		)

		summary = self.context_manager.get_summary()
		logger.info(f'\n{"=" * 60}')
		logger.info('PAPER GENERATION COMPLETE')
		logger.info(f'{"=" * 60}')
		logger.info(f'Output: {output_path}')
		logger.info(f'Total sections: {summary["total_sections"]}')
		logger.info(f'Total words: {summary["total_words"]:,}')
		logger.info(f'Total citations: {summary["total_citations"]}')
		logger.info(f'{"=" * 60}')

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
