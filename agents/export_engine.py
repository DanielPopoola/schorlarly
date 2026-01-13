import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


class ChapterDefinition:
	def __init__(self, number: int, title: str, sections: list[str]):
		self.number = number
		self.title = title
		self.sections = [s.lower() for s in sections]

	def matches_section(self, section_title: str) -> bool:
		t = section_title.lower()
		return any(s in t or t in s for s in self.sections)


class ExportEngine:
	def __init__(self, profile_name: str, output_dir: Path | str = 'output'):
		self.profile_name = profile_name
		self.output_dir = Path(output_dir)
		self.output_dir.mkdir(parents=True, exist_ok=True)
		self.chapters = self._get_chapter_definitions()

	def _get_chapter_definitions(self) -> list[ChapterDefinition]:
		if self.profile_name == 'engineering':
			return [
				ChapterDefinition(
					1,
					'Introduction',
					[
						'introduction',
						'background to the study',
						'statement of the problem',
						'objective of the study',
						'significance',
						'scope of the study',
						'limitations',
						'organization of the study',
						'definition of terms',
					],
				),
				ChapterDefinition(
					2, 'Literature Review', ['existing approach', 'effort to counter', 'specific approach']
				),
				ChapterDefinition(
					3,
					'System Analysis and Design',
					[
						'system analysis',
						'method of data collection',
						'problem of the current system',
						'objective of the new system',
						'menu specification',
						'overview of the system flowchart',
						'procedural flowchart',
						'system design',
					],
				),
				ChapterDefinition(
					4,
					'System Implementation and Documentation',
					[
						'system implementation',
						'system requirement',
						'hardware requirement',
						'software requirement',
						'test-run',
						'program documentation',
						'user manual',
						'system maintenance',
					],
				),
				ChapterDefinition(
					5, 'Summary, Conclusion and Recommendation', ['summary', 'conclusion', 'recommendation']
				),
			]
		else:  # management/general
			return [
				ChapterDefinition(
					1,
					'Introduction',
					[
						'introduction',
						'background to the study',
						'statement of the problem',
						'objective of the study',
						'significance',
						'scope of the study',
						'limitations',
						'organization of the study',
						'definition of terms',
					],
				),
				ChapterDefinition(
					2,
					'Literature Review',
					['introduction', 'theoretical framework', 'conceptual framework', 'empirical studies', 'appraisal'],
				),
				ChapterDefinition(
					3,
					'Methodology',
					[
						'research design',
						'population of the study',
						'sample and sampling',
						'instrument for data collection',
						'validity of the instrument',
						'reliability of the instrument',
						'procedure for data collection',
						'method of data analysis',
					],
				),
				ChapterDefinition(
					4, 'Results', ['answers to research questions', 'testing of hypotheses', 'summary of the findings']
				),
				ChapterDefinition(
					5,
					'Discussion, Conclusion and Recommendation',
					['discussion of the findings', 'implications of the study', 'conclusion', 'recommendation'],
				),
			]

	def export_paper(
		self,
		sections_dir: Path,
		sources_db: dict[str, dict[str, Any]],
		metadata: dict[str, Any],
		formats: tuple[str, ...] = ('pdf', 'docx'),
	) -> dict[str, Path]:
		markdown_content = self._build_complete_markdown(sections_dir, sources_db, metadata)
		md_file = self.output_dir / f'{metadata["topic"][:50].replace(" ", "_")}.md'
		md_file.write_text(markdown_content, encoding='utf-8')

		outputs = {'markdown': md_file}

		for fmt in formats:
			if fmt == 'pdf':
				outputs['pdf'] = self._convert_to_pdf(md_file, metadata)
			elif fmt == 'docx':
				outputs['docx'] = self._convert_to_docx(md_file, metadata)

		return outputs

	def _build_complete_markdown(
		self, sections_dir: Path, sources_db: dict[str, dict[str, Any]], metadata: dict[str, Any]
	) -> str:
		parts = [self._build_title_page(metadata), self._build_abstract(metadata)]

		section_files = sorted(sections_dir.glob('*.md'))
		sections = []
		for f in section_files:
			title = f.stem.split('_', 1)[1].replace('_', ' ').title()
			content = f.read_text(encoding='utf-8')
			if content.startswith('#'):
				content = '\n'.join(content.split('\n')[1:]).strip()
			sections.append({'title': title, 'content': content})

		grouped = self._group_sections_by_chapter(sections)

		for chapter_num, chapter_title, chapter_sections in grouped:
			parts.append(
				f'\n\\newpage\n\n# CHAPTER {self._number_to_word(chapter_num).upper()}: {chapter_title.upper()}\n\n'
			)

			for section in chapter_sections:
				parts.append(f'## {section["title"]}\n\n')
				parts.append(f'{section["content"]}\n\n')

		parts.append(self._build_references(sources_db))
		return ''.join(parts)

	def _group_sections_by_chapter(self, sections: list[dict]) -> list[tuple[int, str, list[dict]]]:
		grouped = []
		for chapter in self.chapters:
			chapter_sections = [s for s in sections if chapter.matches_section(s['title'])]
			if chapter_sections:
				grouped.append((chapter.number, chapter.title, chapter_sections))

		unmatched = [s for s in sections if not any(chapter.matches_section(s['title']) for chapter in self.chapters)]
		if unmatched:
			grouped.append((len(self.chapters) + 1, 'Additional Sections', unmatched))

		return grouped

	def _build_title_page(self, metadata: dict) -> str:
		return f'''---
title: "{metadata['topic']}"
date: "{datetime.now().strftime('%B %d, %Y')}"
geometry: margin=1in
fontsize: 12pt
fontfamily: times
linestretch: 2
header-includes: |
  \\usepackage{{setspace}}
  \\doublespacing
---

\\begin{{titlepage}}
\\centering
\\vspace*{{2cm}}

{{\\Large\\textbf{{{metadata['topic']}}}}}

\\vspace{{2cm}}

{{\\large A Research Project}}

\\vspace{{1cm}}

{{\\large Submitted in Partial Fulfillment}}

{{\\large of the Requirements}}

\\vspace{{2cm}}

\\vspace{{2cm}}

{{\\large {datetime.now().strftime('%B %Y')}}}

\\end{{titlepage}}

\\newpage

'''

	def _build_abstract(self, metadata: dict) -> str:
		abstract = metadata.get('abstract', 'This research paper explores ' + metadata['topic'])
		return f"""## ABSTRACT

{abstract}

\\newpage

"""

	def _build_references(self, sources_db: dict[str, dict[str, Any]]) -> str:
		if not sources_db:
			return '\n## REFERENCES\n\nNo references cited.\n'

		refs = ['\\newpage\n\n## REFERENCES\n\n']

		for _, source in sorted(sources_db.items(), key=lambda x: x[1].get('authors', [''])[0]):
			authors = ', '.join(source.get('authors', ['Unknown']))
			year = source.get('year', 'n.d.')
			title = source.get('title', 'Untitled')
			url = source.get('url', '')

			ref = f'**{authors}** ({year}). *{title}*.'
			if url:
				ref += f' Retrieved from {url}'

			refs.append(f'{ref}\n\n')

		return ''.join(refs)

	def _convert_to_pdf(self, md_file: Path, metadata: dict) -> Path:
		pdf_file = md_file.with_suffix('.pdf')

		try:
			subprocess.run(
				[
					'pandoc',
					str(md_file),
					'-o',
					str(pdf_file),
					'--pdf-engine=xelatex',
					'-V',
					'geometry:margin=1in',
					'-V',
					'fontsize=12pt',
					'-V',
					'mainfont=Times New Roman',
					'-V',
					'linestretch=2',
					'--number-sections',
					'--highlight-style=tango',
				],
				check=True,
				capture_output=True,
			)

			return pdf_file
		except subprocess.CalledProcessError as e:
			raise RuntimeError(f'Pandoc PDF conversion failed: {e.stderr.decode()}') from e
		except FileNotFoundError as e:
			raise RuntimeError(
				'Pandoc not installed. Install with: brew install pandoc (macOS) or \
					apt-get install pandoc texlive-xetex (Linux)'
			) from e

	def _convert_to_docx(self, md_file: Path, metadata: dict) -> Path:
		docx_file = md_file.with_suffix('.docx')

		reference_docx = self._create_reference_docx()

		try:
			subprocess.run(
				[
					'pandoc',
					str(md_file),
					'-o',
					str(docx_file),
					'--reference-doc',
					str(reference_docx),
					'--toc',
					'--number-sections',
				],
				check=True,
				capture_output=True,
			)

			return docx_file
		except subprocess.CalledProcessError as e:
			raise RuntimeError(f'Pandoc DOCX conversion failed: {e.stderr.decode()}') from e

	def _create_reference_docx(self) -> Path:
		ref_path = self.output_dir / 'reference.docx'

		if ref_path.exists():
			return ref_path

		with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_md:
			temp_md.write('# Sample\n\nContent')

		try:
			subprocess.run(
				['pandoc', temp_md.name, '-o', str(ref_path), '--print-default-data-file', 'reference.docx'],
				check=True,
				capture_output=True,
			)
		finally:
			Path(temp_md.name).unlink()

		return ref_path

	def _number_to_word(self, n: int) -> str:
		words = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN']
		return words[n] if n < len(words) else str(n)
