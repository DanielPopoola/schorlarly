from pathlib import Path
from dotenv import load_dotenv

from src.core.orchestrator import Orchestrator

load_dotenv()


def test_full_flow():
	"""Test end-to-end flow."""
	print('Testing Full Flow...\n')
	print('=' * 60)

	# Create orchestrator
	orchestrator = Orchestrator('test_full_flow')
	print('✓ Orchestrator created')

	# Load input
	input_file = Path('input/example_course_registration.md')

	if not input_file.exists():
		print(f'\nError: {input_file} not found')
		print('Create this file first or use your own input file')
		return

	orchestrator.load_input(input_file)
	print(f'✓ Input loaded: {orchestrator.project_input.title}')

	# Show what would happen
	print('\n' + '=' * 60)
	print('Generation Plan:')
	print('=' * 60)

	progress = orchestrator.get_progress()
	print(f'\nTotal sections to generate: {progress["total_sections"]}')
	print(f'\nFirst 5 sections:')

	for i, section in enumerate(orchestrator.sections[:5], 1):
		print(f'\n{i}. {section.name}')
		print(f'   Type: {section.type}')
		print(f'   Word count: {section.word_count["min"]}-{section.word_count["max"]}')
		print(f'   Dependencies: {section.depends_on or "None"}')

	print(f'\n... and {len(orchestrator.sections) - 5} more sections')

	print('\n' + '=' * 60)
	print('✓ Full flow test complete!')
	print('=' * 60)

	print('\nNext: Implement section generators to actually generate content')


if __name__ == '__main__':
	test_full_flow()
