import base64
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class DiagramRenderer:
	def __init__(self, output_dir: Path):
		self.output_dir = output_dir
		self.output_dir.mkdir(parents=True, exist_ok=True)

	def render_mermaid_to_png(self, mermaid_code: str, filename: str) -> Path | None:
		try:
			encoded = base64.urlsafe_b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
			url = f'https://mermaid.ink/img/{encoded}'
			response = requests.get(url, timeout=30)
			response.raise_for_status()
			output_path = self.output_dir / f'{filename}.png'
			with open(output_path, 'wb') as f:
				f.write(response.content)

			logger.info(f'Rendered diagram to: {output_path}')
			return output_path

		except Exception as e:
			logger.error(f'Failed to render Mermaid diagram: {e}')
			logger.debug(f'Mermaid code was: {mermaid_code}')
			return

	def render_all_diagrams(self, section_contexts: list) -> dict[str, Path]:
		rendered_diagrams = {}
		diagram_counter = 1

		for section_ctx in section_contexts:
			if not section_ctx.diagrams:
				continue

			for diagram in section_ctx.diagrams:
				filename = f'diagram_{diagram_counter:02d}_{section_ctx.name.lower().replace(" ", "_")}'

				image_path = self.render_mermaid_to_png(diagram['code'], filename)

				if image_path:
					rendered_diagrams[f'{section_ctx.name}_{diagram["type"]}'] = {
						'path': image_path,
						'caption': diagram.get('caption', 'System Diagram'),
					}
					diagram_counter += 1

		return rendered_diagrams
