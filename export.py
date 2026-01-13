#!/usr/bin/env python
"""
Export CLI - Export generated papers to PDF/DOCX

Usage:
    python export.py                    # Export from default state/ directory
    python export.py --state-dir my_paper/state
    python export.py --format pdf       # Only PDF
    python export.py --format docx      # Only DOCX
"""

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

from agents.export_engine import ExportEngine
from agents.research_agent import ResearchAgent
from utils.logger import logger


def export_paper(
	state_dir: Path, formats: tuple[str, ...] = ('pdf', 'docx'), output_dir: Path | None = None
) -> dict[str, Path]:
	"""Export generated paper to specified formats"""

	state_file = state_dir / 'state.json'
	plan_file = state_dir / 'plan.json'
	sections_dir = state_dir / 'sections'

	# Validate files exist
	if not state_file.exists():
		raise FileNotFoundError(f'State file not found: {state_file}')
	if not plan_file.exists():
		raise FileNotFoundError(f'Plan file not found: {plan_file}')
	if not sections_dir.exists() or not list(sections_dir.glob('*.md')):
		raise FileNotFoundError(f'No sections found in {sections_dir}')

	# Load metadata
	with open(state_file) as f:
		state = json.load(f)
	with open(plan_file) as f:
		plan = json.load(f)

	# Load sources
	research_agent = ResearchAgent(storage_dir=state_dir / 'sources')

	# Determine output directory
	if output_dir is None:
		output_dir = state_dir.parent / 'output'

	# Initialize export engine
	profile_name = state.get('profile_name', 'management')
	export_engine = ExportEngine(profile_name=profile_name, output_dir=output_dir)

	# Build metadata
	metadata = {
		'topic': state['config']['topic'],
		'author': state['config'].get('author', 'Anonymous'),
		'abstract': _generate_abstract(sections_dir, plan['topic']),
		'created_at': state['created_at'],
		'profile': profile_name,
	}

	logger.info(f'\n{"=" * 60}')
	logger.info(f'EXPORTING: {metadata["topic"][:50]}...')
	logger.info(f'Profile: {profile_name}')
	logger.info(f'Formats: {", ".join(formats)}')
	logger.info(f'{"=" * 60}\n')

	# Export
	outputs = export_engine.export_paper(
		sections_dir=sections_dir, sources_db=research_agent.sources_db, metadata=metadata, formats=formats
	)

	logger.info(f'\n{"=" * 60}')
	logger.info('EXPORT COMPLETE')
	logger.info(f'{"=" * 60}')
	for fmt, path in outputs.items():
		logger.info(f'  {fmt.upper():8s}: {path}')
	logger.info(f'{"=" * 60}\n')

	return outputs


def _generate_abstract(sections_dir: Path, topic: str) -> str:
	"""Generate abstract from introduction or first section"""
	intro_files = list(sections_dir.glob('00_*.md'))

	if not intro_files:
		return f'This research examines {topic}.'

	content = intro_files[0].read_text(encoding='utf-8')

	# Remove markdown header
	if content.startswith('#'):
		lines = content.split('\n')
		content = '\n'.join(lines[1:]).strip()

	# Extract first 3 sentences
	sentences = content.replace('\n', ' ').split('. ')
	abstract = '. '.join(s.strip() for s in sentences[:3] if s.strip())

	if not abstract.endswith('.'):
		abstract += '.'

	# Limit to 250 words
	words = abstract.split()
	if len(words) > 250:
		abstract = ' '.join(words[:250]) + '...'

	return abstract


def main():
	parser = ArgumentParser(description='Export generated academic papers')
	parser.add_argument(
		'--state-dir', type=Path, default=Path('state'), help='Directory containing paper state (default: state/)'
	)
	parser.add_argument('--output-dir', type=Path, default=None, help='Output directory for exports (default: output/)')
	parser.add_argument(
		'--format',
		choices=['pdf', 'docx', 'markdown'],
		action='append',
		help='Export formats (can specify multiple times, default: pdf and docx)',
	)

	args = parser.parse_args()

	formats = args.format or ('pdf', 'docx')
	try:
		export_paper(state_dir=args.state_dir, formats=formats, output_dir=args.output_dir)
		return 0

	except FileNotFoundError as e:
		logger.error(f'Error: {e}')
		logger.error('\nMake sure you have run paper generation first:')
		logger.error('  python run.py examples/your_paper.json')
		return 1

	except RuntimeError as e:
		logger.error(f'Export failed: {e}')

		if 'Pandoc' in str(e):
			logger.error('\nPandoc is required for PDF/DOCX export.')
			logger.error('Install it:')
			logger.error('  macOS:   brew install pandoc')
			logger.error('  Ubuntu:  sudo apt-get install pandoc texlive-xetex')
			logger.error('  Windows: Download from https://pandoc.org/installing.html')

		return 1

	except Exception as e:
		logger.error(f'Unexpected error: {e}')
		import traceback

		traceback.print_exc()
		return 1


if __name__ == '__main__':
	sys.exit(main())
