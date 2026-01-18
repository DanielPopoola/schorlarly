from pathlib import Path
from PIL import Image
from src.export.diagram_renderer import DiagramRenderer


def test_diagram_fits_a4():
	"""Verify rendered diagrams fit within A4 page"""

	renderer = DiagramRenderer(Path('output/test_diagrams'))

	# Complex diagram that might be large
	mermaid_code = """
graph TB
    subgraph "Client Layer"
        A[React SPA]
        B[Chart.js]
        C[Axios]
    end
    
    subgraph "Application Layer"
        D[Express API]
        E[JWT Auth]
        F[Middleware]
    end
    
    subgraph "Intelligence Layer"
        G[Flask Service]
        H[LSTM Model]
        I[TensorFlow]
    end
    
    subgraph "Data Layer"
        J[MongoDB]
        K[Redis Cache]
    end
    
    A --> D
    D --> G
    G --> H
    H --> I
    D --> J
    D --> K
    """

	image_path = renderer.render_mermaid_to_png(mermaid_code, 'test_architecture')

	assert image_path.exists(), 'Image not rendered'

	# Check dimensions
	with Image.open(image_path) as img:
		width, height = img.size
		width_inches = width / 96
		height_inches = height / 96

		print(f'\nRendered dimensions: {width}×{height}px ({width_inches:.2f}" × {height_inches:.2f}")')
		print(f'Max allowed: {renderer.MAX_WIDTH}×{renderer.MAX_HEIGHT}px')

		# Must fit within A4 with margins
		assert width <= renderer.MAX_WIDTH, f'Width {width}px exceeds max {renderer.MAX_WIDTH}px'
		assert height <= renderer.MAX_HEIGHT, f'Height {height}px exceeds max {renderer.MAX_HEIGHT}px'

		print('✅ Diagram fits within A4 page')


if __name__ == '__main__':
	test_diagram_fits_a4()
