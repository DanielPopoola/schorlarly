import logging
from typing import TYPE_CHECKING, Any

from src.core.config_loader import SectionConfig
from src.core.context_manager import SectionContext
from src.generators.base import BaseGenerator
from src.llm.client import LLMClient
from src.parsers.input_parser import ProjectInput
from src.research.searcher import ResearchSearcher
from src.research.validator import CitationValidator

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
	from src.core.context_manager import ContextManager


class ResearchSectionGenerator(BaseGenerator):
	def __init__(
		self,
		llm_client: LLMClient,
		config: dict[str, Any],
		research_searcher: ResearchSearcher,
		citation_validator: CitationValidator,
		context_manager: 'ContextManager',
	):
		super().__init__(llm_client, config, context_manager)
		self.research_searcher = research_searcher
		self.citation_validator = citation_validator

	def generate(
		self, section_config: SectionConfig, user_input: ProjectInput | None, context: dict[str, Any]
	) -> SectionContext:
		logger.info(f'Generating research section: {section_config.name}')

		domain = user_input.domain if user_input else 'computer science'
		keywords = user_input.keywords if user_input else []

		search_query = self._build_search_query(section_config.name, domain, keywords, user_input)

		research_config = section_config.research or {}
		max_citations = research_config.get('max_citations', 10)

		logger.info(f'Searching for papers: {search_query}')
		papers = self.research_searcher.search(search_query, max_results=max_citations * 2)

		if not papers:
			logger.warning('No papers found, generating without research')
			papers = []

		validation_results = self.citation_validator.validate_batch(papers, keywords)

		valid_papers = [p for p in papers if validation_results[p.url or p.title].status in ['accepted', 'flagged']]

		logger.info(f'Using {len(valid_papers)} validated papers')

		if len(valid_papers) == 0 and len(papers) > 0:
			self.research_searcher.mark_query_failed(search_query, max_citations * 2)

		paper_citations = {}
		citation_numbers = []
		for paper in valid_papers:
			global_num = self.context_manager.register_paper(paper)
			paper_citations[global_num] = paper
			citation_numbers.append(global_num)

		logger.info(f'Registered citations: {citation_numbers}')

		base_prompt = self._build_base_prompt(section_config, context)
		research_prompt = self._build_research_prompt(section_config, valid_papers, user_input, citation_numbers)

		full_prompt = base_prompt + research_prompt

		content = self.llm_client.generate(
			full_prompt, temperature=0.7, max_tokens=section_config.word_count['max'] * 2
		)
		content = self._remove_section_title_from_content(content, section_config.name)
		valid, word_count = self._validate_word_count(
			content, section_config.word_count['min'], section_config.word_count['max']
		)

		if not valid:
			logger.info(f'Adjusting word count from {word_count} to target range')
			content = self._adjust_content_length(
				content, section_config.word_count['min'], section_config.word_count['max'], section_config.name
			)
			word_count = self._count_words(content)

		key_points = self._extract_key_points_local(content)
		citations = self._extract_citations(content)

		logger.info(f'Generated {word_count} words, {len(key_points)} key points, {len(citations)} citations')

		paper_references = [
			{
				'number': num,
				'title': paper.title,
				'authors': paper.authors,
				'year': paper.year,
				'url': paper.url,
				'source': paper.source,
			}
			for num, paper in sorted(paper_citations.items())
		]

		return SectionContext(
			name=section_config.name,
			content=content,
			key_points=key_points,
			citations=citations,
			word_count=word_count,
			terms_defined=[],
			paper_references=paper_references,
		)

	def _build_search_query(
		self, section_name: str, domain: str, keywords: list[str], user_input: ProjectInput | None
	) -> str:
		if 'background' in section_name.lower():
			# Background needs broad domain overview
			return self.research_searcher.build_search_query(
				domain, keywords, user_input.problem_statement if user_input else ''
			)

		elif 'existing' in section_name.lower() or 'approach' in section_name.lower():
			# Existing approaches needs specific solutions
			problem = user_input.problem_statement if user_input else ''
			return f'{domain} {problem[:200]} existing solutions approaches'

		else:
			# Default: use domain + keywords
			return ' '.join([domain] + keywords[:5])

	def _build_research_prompt(
		self,
		section_config: SectionConfig,
		papers: list[Any],
		user_input: ProjectInput | None,
		citation_numbers: list[int],
	) -> str:
		section_name = section_config.name

		papers_text = '\n\n'.join(
			[
				f'[{citation_numbers[i]}] {p.title}\n'
				f'Authors: {", ".join(p.authors[:3])}\n'
				f'Year: {p.year}\n'
				f'Abstract: {p.abstract[:300]}...'
				for i, p in enumerate(papers[: len(citation_numbers)])  # Match papers to their numbers
			]
		)

		if 'background' in section_name.lower():
			focus = f"""Write a comprehensive background section covering:
	- Historical context of {user_input.domain if user_input else 'the field'}
	- Current state of research
	- Key developments and trends
	- Foundation for understanding the problem

	Synthesize information from these papers into a coherent narrative.
	DO NOT just list papers - weave them into the discussion.

	IMPORTANT: Use the EXACT citation numbers shown below. Do NOT renumber them as [1], [2], [3].
	For example, if a paper is marked [5], cite it as [5] in your text, not [1]."""

		elif 'existing' in section_name.lower():
			focus = """Analyze existing approaches to the problem:
	- What solutions already exist?
	- What are their strengths?
	- What are their limitations?
	- How do they relate to each other?

	Reference specific papers when discussing each approach.

	IMPORTANT: Use the EXACT citation numbers shown below."""

		else:
			focus = """Synthesize these research findings into a coherent academic section.

	IMPORTANT: Use the EXACT citation numbers shown below."""

		prompt = f"""
	{focus}

	RESEARCH PAPERS (use these exact citation numbers):
	{papers_text if papers else 'No specific papers provided. Use general knowledge of the field.'}

	PROJECT CONTEXT:
	Domain: {user_input.domain if user_input else 'Not specified'}
	Problem: {user_input.problem_statement[:300] if user_input else 'Not specified'}

	Write the section now:"""

		return prompt
