import argparse
import sys

from dotenv import load_dotenv

from src.core.orchestrator import Orchestrator


def main():
	load_dotenv()

	parser = argparse.ArgumentParser(description='Schorlarly')
	parser.add_argument('project_name', help='Name of your project')
	parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
	parser.add_argument('--reset', action='store_true', help='Reset and start fresh')
	parser.add_argument('--progress', action='store_true', help='Show current progress')

	args = parser.parse_args()

	orchestrator = Orchestrator(args.project_name)

	if args.reset:
		confirm = input('Are you sure you want to reset all progress? (yes/no): ')
		if confirm.lower() == 'yes':
			orchestrator.reset()
			print('Progress reset successfully')
		else:
			print('Reset cancelled')
		return

	if args.progress:
		progress = orchestrator.get_progress()
		print(f'\nProject: {args.project_name}')
		print(f'Progress: {progress["completed"]}/{progress["total_sections"]} sections')
		print(f'Percentage: {progress["progress_percentage"]:.1f}%')
		print(f'Current section: {progress["current_section"]}')
		print(f'Failed sections: {progress["failed"]}')
		return

	if args.resume:
		print('Resuming paper generation...')
		orchestrator.resume()
	else:
		print('Starting paper generation...')
		orchestrator.generate_paper()


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print('\n\nGeneration interrupted. Run with --resume to continue.')
		sys.exit(0)
	except Exception as e:
		print(f'\nError: {e}')
		sys.exit(1)
