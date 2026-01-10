import json
import sys
from pathlib import Path

from agents.input_validator import ValidationError
from orchestrator import Orchestrator
from utils.logger import logger


def main():
	if len(sys.argv) != 2:
		print('Usage: python run.py <input.json>')
		print('\nExample:')
		print('  python run.py examples/microplastics.json')
		sys.exit(1)

	input_file = Path(sys.argv[1])

	if not input_file.exists():
		print(f'Error: Input file not found: {input_file}')
		sys.exit(1)

	try:
		with open(input_file) as f:
			input_data = json.load(f)
	except json.JSONDecodeError as e:
		print(f'Error: Invalid JSON in {input_file}')
		print(f'  {e}')
		sys.exit(1)

	try:
		orchestrator = Orchestrator(state_dir='state')

		logger.info('=' * 60)
		logger.info('PHASE 1: INITIALIZATION')
		logger.info('=' * 60)
		orchestrator.initialize(input_data)

		logger.info('\n' + '=' * 60)
		logger.info('PHASE 1: EXECUTION SIMULATION')
		logger.info('=' * 60)
		orchestrator.run()

	except ValidationError as e:
		logger.error(f'Validation failed: {e}')
		sys.exit(1)
	except Exception as e:
		logger.error(f'Unexpected error: {e}')
		raise


if __name__ == '__main__':
	main()
