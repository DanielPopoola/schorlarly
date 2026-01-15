import logging
import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from src.core.context_manager import ContextManager

logger = logging.getLogger(__name__)


def create_word_exporter_from_config(context_manager: ContextManager, config: dict) -> 'WordExporter':
	"""Factory function for creating exporter"""
	output_config = config.get('output', {})
	citation_config = config.get('citation', {})

	export_config = {'final_dir': output_config.get('final_dir', 'output/final'), 'citation': citation_config}

	return WordExporter(context_manager, export_config)


class WordExporter:
	def __init__(self, context_manager: ContextManager, config: dict):
		self.context_manager = context_manager
		self.output_dir = Path(config.get('final_dir', 'output/final'))
		self.citation_style = config.get('citation', {}).get('style', 'IEEE')

	def export(self, project_name: str, project_title: str, author: str) -> Path:
		logger.info(f'Exporting paper to Word: {project_name}')

		doc = Document()
		self._setup_document_style(doc)
		self._add_title_page(doc, project_title, author)
		self._add_sections(doc)
		self._add_references(doc)

		self.output_dir.mkdir(parents=True, exist_ok=True)
		output_path = self.output_dir / f'{project_name}.docx'
		doc.save(output_path)

		logger.info(f'Paper exported to: {output_path}')
		return output_path

	def _setup_document_style(self, doc: Document):
		style = doc.styles['Normal']
		font = style.font
		font.name = 'Times New Roman'
		font.size = Pt(12)

		paragraph_format = style.paragraph_format
		paragraph_format.line_spacing = 1.5
		paragraph_format.space_after = Pt(6)

		# Setup page margins (1 inch standard)
		sections = doc.sections
		for section in sections:
			section.top_margin = Inches(1)
			section.bottom_margin = Inches(1)
			section.left_margin = Inches(1)
			section.right_margin = Inches(1)

	def _add_title_page(self, doc: Document, title: str, author: str):
		"""Create title page"""
		# Add some space
		for _ in range(6):
			doc.add_paragraph()

		# Title (centered, large)
		title_para = doc.add_heading(title, 0)
		title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

		doc.add_paragraph()  # Space

		# Author (centered)
		author_para = doc.add_paragraph(f'By\n{author}')
		author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

		doc.add_paragraph()  # Space

		# Date (centered)
		date_para = doc.add_paragraph(datetime.now().strftime('%B %Y'))
		date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

		# Page break after title page
		doc.add_page_break()

	def _add_sections(self, doc: Document):
		"""Add all sections in order"""
		for section_name in self.context_manager.section_order:
			section_ctx = self.context_manager.get_section(section_name)
			if not section_ctx:
				continue

			logger.debug(f'Adding section: {section_name}')

			# Section heading
			doc.add_heading(section_name, 1)

			# Convert markdown content to Word
			self._add_markdown_content(doc, section_ctx.content)

			# Small space after section
			doc.add_paragraph()

	def _add_markdown_content(self, doc: Document, markdown_text: str):
		"""Convert markdown to Word formatting"""
		# Split into paragraphs
		paragraphs = markdown_text.split('\n\n')

		for para_text in paragraphs:
			para_text = para_text.strip()
			if not para_text:
				continue

			# Check if it's a list
			if para_text.startswith('- ') or para_text.startswith('* '):
				self._add_bullet_list(doc, para_text)
			elif re.match(r'^\d+\.', para_text):
				self._add_numbered_list(doc, para_text)
			elif para_text.startswith('```'):
				self._add_code_block(doc, para_text)
			else:
				self._add_formatted_paragraph(doc, para_text)

	def _add_formatted_paragraph(self, doc: Document, text: str):
		"""Add paragraph with inline formatting (bold, italic, code)"""
		para = doc.add_paragraph()

		# Split by formatting markers
		parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`)', text)

		for part in parts:
			if not part:
				continue

			if part.startswith('**') and part.endswith('**'):
				# Bold
				run = para.add_run(part[2:-2])
				run.bold = True
			elif part.startswith('*') and part.endswith('*'):
				# Italic
				run = para.add_run(part[1:-1])
				run.italic = True
			elif part.startswith('`') and part.endswith('`'):
				# Code (monospace)
				run = para.add_run(part[1:-1])
				run.font.name = 'Courier New'
				run.font.size = Pt(10)
			else:
				# Normal text
				para.add_run(part)

	def _add_bullet_list(self, doc: Document, text: str):
		"""Add bulleted list"""
		lines = text.split('\n')
		for line in lines:
			line = line.strip()
			if line.startswith('- ') or line.startswith('* '):
				content = line[2:]
				doc.add_paragraph(content, style='List Bullet')

	def _add_numbered_list(self, doc: Document, text: str):
		"""Add numbered list"""
		lines = text.split('\n')
		for line in lines:
			line = line.strip()
			if re.match(r'^\d+\.', line):
				content = re.sub(r'^\d+\.\s*', '', line)
				doc.add_paragraph(content, style='List Number')

	def _add_code_block(self, doc: Document, text: str):
		"""Add code block"""
		# Remove markdown code fence
		code = re.sub(r'^```\w*\n|```$', '', text, flags=re.MULTILINE)

		para = doc.add_paragraph(code.strip())
		para.style = 'Normal'

		# Format as code
		for run in para.runs:
			run.font.name = 'Courier New'
			run.font.size = Pt(10)

		# Light gray background (if possible)
		# Note: python-docx has limited background color support

	def _add_references(self, doc: Document):
		"""Add references section"""
		if not self.context_manager.all_citations:
			logger.info('No citations to add')
			return

		doc.add_page_break()
		doc.add_heading('References', 1)

		unique_citations = sorted(set(self.context_manager.all_citations))

		for citation in unique_citations:
			doc.add_paragraph(citation, style='Normal')

		logger.info(f'Added {len(unique_citations)} citations')
