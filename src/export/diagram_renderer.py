import base64
import logging
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

logger = logging.getLogger(__name__)


class DiagramRenderer:
	MAX_WIDTH = 794 - (2 * 96)
	MAX_HEIGHT = 1123 - (2 * 96)

	def __init__(self, output_dir: Path):
		self.output_dir = output_dir
		self.output_dir.mkdir(parents=True, exist_ok=True)

	def render_mermaid_to_png(self, mermaid_code: str, filename: str) -> Path | None:
		try:
			encoded = base64.urlsafe_b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
			url = f'https://mermaid.ink/img/{encoded}'
			response = requests.get(url, timeout=30)
			response.raise_for_status()

			image = Image.open(BytesIO(response.content))
			original_width, original_height = image.size

			logger.info(f'Original image size: {original_width}×{original_height}px')

			if original_width > self.MAX_WIDTH or original_height > self.MAX_HEIGHT:
				image = self._resize_to_fit(image)
				logger.info(f'Resized to: {image.size[0]}×{image.size[1]}px')

			output_path = self.output_dir / f'{filename}.png'
			image.save(output_path)

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

	def _resize_to_fit(self, image: Image.Image) -> Image.Image:
		original_width, original_height = image.size

		# Calculate scaling factor
		width_ratio = self.MAX_WIDTH / original_width
		height_ratio = self.MAX_HEIGHT / original_height
		scale_factor = min(width_ratio, height_ratio)  # Use smaller ratio

		new_width = int(original_width * scale_factor)
		new_height = int(original_height * scale_factor)

		return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
