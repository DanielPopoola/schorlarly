from pathlib import Path

from src.core.config_loader import SectionConfig, get_config
from src.core.context_manager import ContextManager
from src.generators import GeneratorFactory
from src.llm.client import create_llm_client_from_config
from src.parsers.input_parser import InputParser
from src.research.searcher import ResearchSearcher
from src.research.validator import CitationValidator


def test_generator(generator_type: str):
	"""Test a specific generator type"""
	print(f'\n{"=" * 60}')
	print(f'Testing {generator_type.upper()} Generator')
	print(f'{"=" * 60}\n')

	# Load config
	config = get_config()

	# Initialize components
	llm_client = create_llm_client_from_config(config.get_llm_config())
	parser = InputParser(llm_client)

	research_searcher = ResearchSearcher(config.get_research_config())
	citation_validator = CitationValidator(llm_client, config.get_citation_config())

	context_file = Path('output/state/test_context.json')
	context_manager = ContextManager(context_file)

	config_dict = {'writing': config.get_writing_config(), 'citation': config.get_citation_config()}

	factory = GeneratorFactory(llm_client, config_dict, research_searcher, citation_validator, context_manager)

	# Load test input
	input_file = Path('input/example_course_registration.md')
	user_input = parser.parse_file(input_file)

	# Create test section config
	test_configs = {
		'research': SectionConfig(
			name='Background to the Study',
			type='research',
			word_count={'min': 800, 'max': 1200},
			depends_on=['Introduction'],
			research={'required': True, 'min_citations': 5, 'max_citations': 10},
		),
		'evidence': SectionConfig(
			name='System Design',
			type='evidence',
			word_count={'min': 600, 'max': 1000},
			depends_on=['System Analysis'],
		),
		'interactive': SectionConfig(
			name='Statement of the Problem',
			type='interactive',
			word_count={'min': 200, 'max': 400},
			depends_on=['Background to the Study'],
		),
		'synthesis': SectionConfig(
			name='Summary', type='synthesis', word_count={'min': 400, 'max': 600}, depends_on=[]
		),
		'automated': SectionConfig(
			name='Definition of Terms', type='automated', word_count={'min': 200, 'max': 400}, depends_on=[]
		),
	}

	section_config = test_configs[generator_type]

	# Mock context
	context = {
		'section_name': section_config.name,
		'previously_completed': ['Introduction'],
		'dependent_sections': {},
		'all_citations_used': [],
		'all_terms_defined': [],
		'key_points_covered': ['Course registration is time-consuming', 'Manual process causes errors'],
	}

	# Get generator and generate
	generator = factory.get_generator(generator_type)

	print(f'Generating {section_config.name}...\n')

	try:
		section_context = generator.generate(section_config, user_input, context)

		print('✓ Generated successfully!')
		print(f'\nWord count: {section_context.word_count}')
		print(f'Key points: {len(section_context.key_points)}')
		print(f'Citations: {len(section_context.citations)}')

		print(f'\n{"─" * 60}')
		print('CONTENT PREVIEW (first 500 chars):')
		print(f'{"─" * 60}')
		print(section_context.content[:500])
		print('...')

		print(f'\n{"─" * 60}')
		print('KEY POINTS:')
		print(f'{"─" * 60}')
		for i, point in enumerate(section_context.key_points[:5], 1):
			print(f'{i}. {point}')

		return True

	except Exception as e:
		print(f'✗ Generation failed: {e}')
		import traceback

		traceback.print_exc()
		return False


if __name__ == '__main__':
	import sys

	if len(sys.argv) > 1:
		# Test specific generator
		generator_type = sys.argv[1]
		test_generator(generator_type)
	else:
		# Test all generators
		print('Testing all generators...\n')
		types = ['automated', 'interactive', 'evidence', 'research', 'synthesis']

		results = {}
		for gen_type in types:
			results[gen_type] = test_generator(gen_type)

		print('\n\n' + '=' * 60)
		print('TEST SUMMARY')
		print('=' * 60)
		for gen_type, success in results.items():
			status = '✓ PASS' if success else '✗ FAIL'
			print(f'{gen_type:15} {status}')
