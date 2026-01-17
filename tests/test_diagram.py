from pathlib import Path
from src.core.config_loader import get_config
from src.llm.client import create_llm_client_from_config
from src.parsers.input_parser import InputParser
from src.generators.evidence_section import EvidenceSectionGenerator
from src.core.config_loader import SectionConfig


def test_diagram_generation():
	config = get_config()
	llm_client = create_llm_client_from_config(config.get_llm_config())

	parser = InputParser(llm_client)
	user_input = parser.parse_file(Path('input/example_course_registration.md'))

	# Create a test section config with diagrams
	section_config = SectionConfig(
		name='System Design',
		type='evidence',
		word_count={'min': 500, 'max': 1000},
		depends_on=['System Analysis'],
		diagrams=[
			{'type': 'architecture', 'description': 'System architecture showing frontend, backend, and ML layers'}
		],
	)

	generator_config = {'writing': config.get_writing_config(), 'citation': config.get_citation_config()}

	generator = EvidenceSectionGenerator(llm_client, generator_config)

	context = {'section_name': 'System Design', 'previously_completed': []}

	section_ctx = generator.generate(section_config, user_input, context)

	print(f'Generated {len(section_ctx.diagrams)} diagram(s)')

	if section_ctx.diagrams:
		for i, diagram in enumerate(section_ctx.diagrams):
			print(f'\nDiagram {i + 1}:')
			print(f'Type: {diagram["type"]}')
			print(f'Code:\n{diagram["code"][:200]}...')

			print('\nTesting render to PNG...')
			from src.export.diagram_renderer import DiagramRenderer

			renderer = DiagramRenderer(Path('output/diagrams'))
			image_path = renderer.render_mermaid_to_png(diagram['code'], f'test_diagram_{i + 1}')

			if image_path:
				print(f'✓ Rendered successfully: {image_path}')
				print(f'  File exists: {image_path.exists()}')
				print(f'  File size: {image_path.stat().st_size / 1024:.2f} KB')
			else:
				print('✗ Rendering failed')

	return section_ctx


if __name__ == '__main__':
	test_diagram_generation()
