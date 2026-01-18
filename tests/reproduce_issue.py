import logging
import sys
from pathlib import Path
from src.core.context_manager import ContextManager
from src.export.word_exporter import WordExporter

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def reproduce():
	context_file = Path('output/state/medical_diagnosis_context.json')
	if not context_file.exists():
		print(f'Error: Context file {context_file} not found.')
		return

	print(f'Loading context from {context_file}...')
	context_manager = ContextManager(context_file)
	context_manager.load_state()

	# Check if sections are loaded
	summary = context_manager.get_summary()
	print(f'Loaded {summary["total_sections"]} sections, {summary["total_words"]} words.')

	config = {'output': {'final_dir': 'output/final'}, 'citation': {'style': 'IEEE'}}

	exporter = WordExporter(context_manager, config)

	project_name = 'reproduced_medical_diagnosis'
	project_title = (
		'Design and Implementation of a Privacy-Preserving Medical Diagnosis System using Federated Learning  '
	)
	author = 'Daniel Popoola'

	print(f'Exporting to {project_name}.docx...')
	output_path = exporter.export(project_name, project_title, author)

	if output_path.exists():
		size = output_path.stat().st_size
		print(f'Export successful. File size: {size} bytes')
		if size < 20000:  # Title page and references only would be small
			print('WARNING: File size is suspiciously small. It might only contain the title page and references.')
	else:
		print('Error: Export failed, file not created.')


if __name__ == '__main__':
	reproduce()
