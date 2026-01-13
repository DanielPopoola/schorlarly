import json
import signal
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from agents.context_manager import ContextManager
from agents.export_engine import ExportEngine
from agents.input_validator import InputValidator
from agents.research_agent import ResearchAgent
from agents.source_filter import SourceFilter
from agents.state_manager import StateManager
from agents.validation_agent import CitationValidator
from agents.writing_agent import WritingAgent
from config.settings import settings
from models import Finding, Severity
from models.template_profile import ProfileManager, Section, SectionType
from utils.llm_client import UnifiedLLMClient
from utils.logger import logger


class Orchestrator:
	def __init__(self, state_dir: Path | str = 'state'):
		self.state_dir = Path(state_dir)
		self.state_dir.mkdir(parents=True, exist_ok=True)
		self.state_file = self.state_dir / 'state.json'
		self.plan_file = self.state_dir / 'plan.json'
		self.sections_dir = self.state_dir / 'sections'
		self.sections_dir.mkdir(parents=True, exist_ok=True)

		self.state_manager = StateManager(self.state_dir)
		self.validator = InputValidator()
		self.research_agent = ResearchAgent(
			storage_dir=self.state_dir / 'sources',
			max_papers_per_section=10,
		)
		self._writing_agent = None
		self.llm_client: UnifiedLLMClient = UnifiedLLMClient(
			client=OpenAI(base_url='https://openrouter.ai/api/v1', api_key=settings.OPENROUTER_API_KEY),
			model='xiaomi/mimo-v2-flash:free',
			site_url='https://github.com/DanielPopoola/scholarly',
			app_name='Scholarly',
		)
		self.context_manager = ContextManager(self.llm_client)
		self.profile_manager = ProfileManager()
		self.current_profile = None
		self.export_engine = None

		self._setup_signal_handlers()

		self._current_section_id = None
		self._interruption_requested = False

	def initialize(self, input_data: dict[str, Any]) -> None:
		if self.state_manager.can_resume():
			response = input('\n Found incomplete paper. Resume from checkpoint? (y/n): ')
			if response.lower() == 'y':
				logger.info('Resuming from checkpoint...')
				return

		config = self.validator.validate(input_data)
		logger.info(f'Input validated. Topic: {config["topic"][:50]}...')

		self.current_profile = self.profile_manager.detect(config['template'])
		logger.info(f'Detected template profile: {self.current_profile.name}')

		state = {
			'config': config,
			'profile_name': self.current_profile.name,
			'project_type': config['project_type'],
			'artifacts': config.get('artifacts', []),
			'current_section_id': 0,
			'completed_sections': [],
			'failed_sections': [],
			'research_complete': False,
			'created_at': datetime.now(UTC).isoformat(),
			'updated_at': datetime.now(UTC).isoformat(),
		}
		self._save_state(state)
		logger.info(f'State initialized at {self.state_file}')

		# Generate Global Outline before creating the plan
		global_outline = self._generate_global_outline(config)
		state['global_outline'] = global_outline
		self._save_state(state)

		sections = []
		for idx, title in enumerate(config['template']):
			section_profile = self.current_profile.get_section(title)
			section_guidance = global_outline.get(title, '')

			sections.append(
				{
					'id': idx,
					'title': title,
					'objective': self._generate_objective(title, section_profile),
					'guidance': section_guidance,
					'status': 'pending',
					'word_count': 0,
					'citations_count': 0,
					'min_citations': section_profile.min_citations,
					'max_words': section_profile.max_word_count,
					'section_type': section_profile.type.value,
					'requires_code': section_profile.requires_code,
					'requires_diagrams': section_profile.requires_diagrams,
					'research_strategy': section_profile.research_strategy,
				}
			)

		plan = {
			'topic': config['topic'],
			'sections': sections,
			'total_sections': len(sections),
			'profile': self.current_profile.name,
			'created_at': datetime.now(UTC).isoformat(),
		}
		self._save_plan(plan)
		logger.info(f'Plan created with {len(sections)} sections')
		self.state_manager.clear_checkpoint()

	def run(self) -> None:
		if self.state_manager.can_resume():
			saved = self.state_manager.load_checkpoint()
			state = saved['state']
			plan = saved['plan']
			checkpoint = saved['checkpoint']
			context_cache = saved['context_cache']

			# Restore context manager
			self._restore_context_cache(context_cache)

			start_section = checkpoint['current_section_id']
			logger.info(f'\n{"=" * 60}')
			logger.info('RESUMING FROM CHECKPOINT')
			logger.info(f'{"=" * 60}\n')
			logger.info(f'Completed: {checkpoint["completed_sections"]}')
			logger.info(f'Resuming from: {start_section}')
			logger.info(f'{"=" * 60}\n')
		else:
			state = self._load_state()
			plan = self._load_plan()
			start_section = 0

		if not state.get('research_complete'):
			self._run_global_research(state, plan)

		if self._writing_agent is None:
			self._writing_agent = WritingAgent(self.llm_client)

		# Process sections
		for section in plan['sections'][start_section:]:
			# NEW: Check if section is allowed
			if not self._gate_section(section, state):
				section['status'] = 'skipped'
				self._save_plan(plan)  # Save plan with skipped status
				continue

			# Check for interruption
			if self._interruption_requested:
				logger.warning('\n  Interruption detected, saving...')
				self._save_checkpoint(section['id'], state, plan)
				logger.info('✓ Checkpoint saved. Run again to resume.')
				sys.exit(0)

			self._current_section_id = section['id']

			try:
				self._process_section_with_gap_detection(section, state, plan)

				# Save checkpoint after success
				if section['status'] == 'validated':
					self._save_checkpoint(section['id'], state, plan)

			except KeyboardInterrupt:
				logger.warning('\n Keyboard interrupt - saving...')
				self._save_checkpoint(section['id'], state, plan)
				sys.exit(0)

			except Exception as e:
				logger.error(f'Section {section["id"]} crashed: {e}')
				self._save_checkpoint(section['id'], state, plan)

				response = input('\nContinue with next section? (y/n): ')
				if response.lower() != 'y':
					sys.exit(1)

		self.state_manager.clear_checkpoint()

		logger.info('Paper generation complete!')

		# NEW: Global coherence editing pass
		logger.info(f'\n{"=" * 60}')
		logger.info('PHASE 3: GLOBAL COHERENCE EDITING')
		logger.info(f'{"=" * 60}\n')

		from agents.editor_agent import EditorAgent

		editor = EditorAgent(self.llm_client)

		all_section_contents = []
		for section in plan['sections']:
			content = self._load_section_content(section['id'])
			if content:
				all_section_contents.append(content)

		edited_contents = editor.remove_redundancy(all_section_contents)

		# Save edited versions (Note: currently EditorAgent returns original, needs full implementation)
		for i, section in enumerate(plan['sections']):
			if i < len(edited_contents):
				self._save_section_content(section['id'], section['title'], edited_contents[i])

		self._export_paper(state, plan)

	def _run_global_research(self, state: dict, plan: dict) -> None:
		logger.info(f'\n{"=" * 60}')
		logger.info('PHASE 2: GLOBAL RESEARCH')
		logger.info(f'{"=" * 60}\n')
		logger.info('Conducting research once for entire paper...')

		source_ids = self.research_agent.research_section(
			topic=state['config']['topic'],
			section_title=state['config']['topic'],
			section_objective='Comprehensive research for entire paper',
		)

		plan['global_source_ids'] = source_ids
		state['research_complete'] = True
		self._save_plan(plan)
		self._save_state(state)

		logger.info(f'✓ Global research complete: {len(source_ids)} sources')
		logger.info(f'{"=" * 60}\n')

	def _gate_section(self, section: dict, state: dict) -> bool:
		"""Returns False if section should be skipped"""
		project_type = state['project_type']
		section_title = section['title'].lower()

		# Rule 1: Proposals cannot have Results
		if project_type == 'proposal' and any(
			keyword in section_title for keyword in ['result', 'finding', 'outcome', 'data analysis']
		):
			logger.warning(f"Skipping '{section['title']}' (proposal has no results)")
			return False

		# Rule 2: Reviews cannot have Methodology (for original work)
		if project_type == 'review' and any(
			keyword in section_title for keyword in ['methodology', 'experiment', 'procedure']
		):
			logger.warning(f"Skipping '{section['title']}' (review has no experiments)")
			return False

		# Rule 3: Empirical/Computational require artifacts for Results
		if project_type in ['empirical', 'computational'] and 'result' in section_title:
			has_artifacts = len(state.get('artifacts', [])) > 0
			if not has_artifacts:
				logger.error(f"Cannot write '{section['title']}'—no artifacts provided!")
				return False

		return True

	def _save_checkpoint(self, current_section_id: int, state: dict, plan: dict) -> None:
		completed = [s['id'] for s in plan['sections'] if s['status'] in ['validated', 'drafted']]

		context_summaries = {}
		if hasattr(self, 'context_manager'):
			for summary in self.context_manager.summaries:
				context_summaries[summary.section_id] = {
					'title': summary.section_title,
					'summary': summary.summary,
					'key_findings': [{'text': f.text, 'source_ids': f.source_ids} for f in summary.key_findings],
				}

		self.state_manager.save_checkpoint(
			current_section_id=current_section_id + 1, completed_sections=completed, context_summaries=context_summaries
		)

	def _restore_context_cache(self, context_cache: dict) -> None:
		if not context_cache or not hasattr(self, 'context_manager'):
			return

		from models import Finding, SectionSummary

		for section_id_str, cache_data in context_cache.items():
			section_id = int(section_id_str)

			findings = [
				Finding(text=f['text'], source_ids=f['source_ids'], section_id=section_id)
				for f in cache_data.get('key_findings', [])
			]

			summary = SectionSummary(
				section_id=section_id,
				section_title=cache_data['title'],
				summary=cache_data['summary'],
				key_findings=findings,
				key_terms=[],
			)

			self.context_manager.summaries.append(summary)

		logger.info(f'✓ Restored {len(context_cache)} summaries from cache')

	def _generate_global_outline(self, config: dict) -> dict[str, str]:
		logger.info('Generating global outline for cohesive narrative...')

		sections_list = '\n'.join([f'- {s}' for s in config['template']])
		artifacts_text = '\n'.join([f'- {a["type"]}: {a["description"]}' for a in config.get('artifacts', [])])

		prompt = f"""You are a senior academic editor. Create a detailed global outline for a research project.

# TOPIC
{config['topic']}

# PROJECT TYPE
{config['project_type']}
(Empirical: user collected data; Computational: user wrote code; Review: literature synthesis only; 
Proposal: future work)

# AVAILABLE ARTIFACTS (EVIDENCE OF WORK DONE)
{artifacts_text if artifacts_text else 'NONE - NO ORIGINAL WORK PERFORMED'}

# SECTIONS TO COVER
{sections_list}

# TASK
For each section, provide 2-3 sentences of specific guidance. 
Ensure:
1. No circular definitions (don't repeat problem statement in intro AND background).
2. Epistemic Integrity: If PROJECT TYPE is 'Review' or 'Proposal', FORBID claims of ownership (e.g., no "we measured").
3. Logical Flow: Each section must build on the previous one.
4. Content Mapping: Assign specific sub-topics to specific sections so they don't overlap.

# OUTPUT FORMAT
JSON dictionary where keys are section titles and values are the guidance.
Only output the JSON.
"""
		try:
			response = self.llm_client.generate(prompt, max_tokens=2000)
			# Strip markdown if any
			if '```json' in response:
				response = response.split('```json')[1].split('```')[0].strip()
			elif '```' in response:
				response = response.split('```')[1].split('```')[0].strip()

			return json.loads(response)
		except Exception as e:
			logger.error(f'Global outline generation failed: {e}')
			return {title: 'Standard academic coverage' for title in config['template']}

	def _generate_objective(self, title: str, profile: Section) -> str:
		objectives = {
			SectionType.INTRO_CONCLUSION: {
				'introduction': 'Introduce the research problem, establish context, and state objectives',
				'background': 'Provide comprehensive background on the domain and establish research context',
				'statement': 'Clearly define the research problem and its significance',
				'objective': 'State specific, measurable objectives of the study',
				'significance': 'Justify the importance and potential impact of the research',
				'scope': 'Define boundaries and limitations of the study',
				'summary': 'Recapitulate key findings and their implications',
				'conclusion': 'Synthesize findings and state final conclusions',
				'recommendations': 'Provide actionable recommendations based on findings',
			},
			SectionType.LITERATURE: {
				'literature': 'Review and synthesize existing research, identify gaps',
				'existing': 'Analyze existing approaches and their limitations',
				'efforts': 'Evaluate prior attempts to address the problem',
			},
			SectionType.METHODOLOGY: {
				'methodology': 'Describe research methods, procedures, and justification',
				'approach': 'Detail the specific approach and rationale',
			},
			SectionType.TECHNICAL: {
				'analysis': 'Analyze system requirements and constraints',
				'design': 'Present system architecture and design decisions',
				'flowchart': 'Illustrate process flows and system logic',
			},
			SectionType.IMPLEMENTATION: {
				'implementation': 'Document implementation details and technical choices',
				'test': 'Describe testing procedures and results',
				'documentation': 'Provide technical and user documentation',
				'maintenance': 'Outline maintenance procedures and support',
			},
			SectionType.DISCUSSION: {
				'findings': 'Present and analyze research findings',
				'discussion': 'Interpret results and discuss implications',
				'results': 'Report research outcomes with supporting evidence',
			},
		}

		title_lower = title.lower()
		section_objectives = objectives.get(profile.type, {})

		for keyword, objective in section_objectives.items():
			if keyword in title_lower:
				return objective

		return f'Address the requirements of the {title} section'

	def _refine_objective(
		self, section_title: str, initial_objective: str, topic: str, prior_findings: list[Finding]
	) -> str:
		if not prior_findings:
			return initial_objective

		findings_text = '\n'.join(f'- {f.text}' for f in prior_findings)

		prompt = f"""You are planning an academic paper section.

# Paper Topic
{topic}

# Section to Write
{section_title}

# Initial Objective (Generic)
{initial_objective}

# Key Findings from Prior Sections
{findings_text}

# Task
Refine the objective for "{section_title}" to build upon these specific findings.
Make it concrete and actionable for the writer.

Output only the refined objective (1-2 sentences)."""

		refined = self.llm_client.generate(prompt, max_tokens=200).strip()
		logger.info(f'  Objective refined: {initial_objective} → {refined}')
		return refined

	def _process_section_with_gap_detection(self, section: dict, state: dict, plan: dict) -> None:
		section_id = section['id']
		# 1. Refine objective based on prior findings
		if section_id > 0:
			self._maybe_refine_objective(section, state, plan)

		# 2. Get section constraints and sources
		config = self._get_section_config(section)
		sources = self._filter_sources(section, plan, config)

		logger.info(f'\n[Section {section_id}] {config}')
		self._log_warnings(section)

		# 3. Write with retries
		for attempt in range(1, config['max_retries'] + 1):
			result = self._attempt_write(section, state, sources, config, attempt)

			if result == 'success':
				self._finalize_section(section, plan, attempt)
				return
			elif result == 'gap_detected':
				sources = self._handle_gap(section, state, sources)
			elif result == 'failed':
				continue

		# 4. Mark as failed after all retries
		self._mark_failed(section, state, plan)

	def _maybe_refine_objective(self, section: dict, state: dict, plan: dict) -> None:
		"""Refine objective based on introduction findings"""
		intro_findings = self.context_manager.extract_findings_for_refinement(0)
		if not intro_findings:
			return

		refined = self._refine_objective(
			section_title=section['title'],
			initial_objective=section['objective'],
			topic=state['config']['topic'],
			prior_findings=intro_findings,
		)
		section['objective'] = refined
		self._save_plan(plan)

	def _get_section_config(self, section: dict) -> dict:
		"""Extract section configuration"""
		return {
			'min_citations': section.get('min_citations', 3),
			'max_words': section.get('max_words', 1500),
			'section_type': section.get('section_type', 'discussion'),
			'max_retries': 3,
		}

	def _filter_sources(self, section: dict, plan: dict, config: dict) -> list:
		"""Filter global sources by relevance"""
		all_sources = [self.research_agent.get_source(sid) for sid in plan.get('global_source_ids', [])]
		all_sources = [s for s in all_sources if s]

		# Choose strategy based on section type
		if section.get('research_strategy') == 'targeted':
			min_score, top_k = 0.3, 8
			strategy = 'targeted'
		else:
			min_score, top_k = 0.2, 4
			strategy = 'global'

		source_filter = SourceFilter()
		filtered = source_filter.filter_by_relevance(
			sources=all_sources, objective=section['objective'], min_score=min_score, top_k=top_k
		)

		logger.info(f'  Filtered {len(all_sources)} → {len(filtered)} ({strategy} strategy)')
		return filtered

	def _log_warnings(self, section: dict) -> None:
		"""Log unimplemented features"""
		if section.get('requires_code'):
			logger.warning('  ⚠️  Section requires code examples (not yet implemented)')
		if section.get('requires_diagrams'):
			logger.warning('  ⚠️  Section requires diagrams (not yet implemented)')

	def _attempt_write(self, section: dict, state: dict, sources: list, config: dict, attempt: int) -> str:
		try:
			# Get context from previous section
			section_id = section['id']
			previous_context = self._get_previous_context(section_id)

			# Write section
			result = self._writing_agent.write_section(  # type: ignore
				section_title=section['title'],
				section_objective=section['objective'],
				topic=state['config']['topic'],
				project_type=state['project_type'],
				artifacts=state.get('artifacts', []),
				guidance=section.get('guidance', ''),
				available_sources=sources,
				style_preferences=state['config']['style'],
				constraints={
					'max_section_word_count': config['max_words'],
					'min_citations_per_section': config['min_citations'],
				},
				previous_section_text=previous_context,
				avoid_repetition=(section_id > 3),  # Only for later sections
			)

			# Validate
			validator = CitationValidator(self.research_agent.sources_db)
			validation = validator.validate_section(
				section_id=section_id,
				content=result['content'],
				project_type=state['project_type'],
				artifacts=state.get('artifacts', []),
				min_citations=config['min_citations'],
				max_words=config['max_words'],
			)

			if validation.passed:
				# Store result for finalization
				self._temp_result = result
				return 'success'

			# Check if we need gap research
			critical_issues = [i for i in validation.issues if i.severity == Severity.CRITICAL]
			if critical_issues and validation.missing_topics:
				self._temp_validation = validation
				logger.warning(f'  Gap detected: {validation.missing_topics}')
				return 'gap_detected'

			logger.warning(f'  Validation failed (attempt {attempt}): {[i.message for i in validation.issues[:3]]}')
			return 'failed'

		except Exception as e:
			logger.error(f'  Writing failed (attempt {attempt}): {e}')
			return 'failed'

	def _get_previous_context(self, section_id: int) -> str | None:
		if section_id == 0:
			return None

		# For early sections (1-3): use full previous section
		if section_id <= 3:
			return self._load_section_content(section_id - 1)

		# For later sections (4+): use compressed summaries
		return self.context_manager.get_context_for_section(current_section_id=section_id, window_size=3)

	def _handle_gap(self, section: dict, state: dict, sources: list) -> list:
		validation = self._temp_validation  # Stored from _attempt_write

		gap_query = f'{state["config"]["topic"]} {" ".join(validation.missing_topics)}'
		new_source_ids = self.research_agent.research_section(
			topic=gap_query, section_title=section['title'], section_objective=section['objective']
		)

		new_sources = [self.research_agent.get_source(sid) for sid in new_source_ids]
		sources.extend([s for s in new_sources if s])

		logger.info(f'  Added {len(new_sources)} gap-filling sources, retrying...')
		return sources

	def _finalize_section(self, section: dict, plan: dict, attempt: int) -> None:
		result = self._temp_result  # Stored from _attempt_write
		section_id = section['id']

		# Save content
		self._save_section_content(section_id, section['title'], result['content'])

		# Summarize for context manager
		if section_id > 0:
			summary = self.context_manager.summarize_section(
				section_id=section_id,
				section_title=section['title'],
				content=result['content'],
				sources_used=result['citations_used'],
			)
			section['summary'] = summary.summary

		# Update metadata
		section['status'] = 'validated'
		section['word_count'] = result['word_count']
		section['citations_count'] = len(result['citations_used'])
		section['completed_at'] = datetime.now().isoformat()
		self._save_plan(plan)

		logger.info(f'  ✓ Section validated (attempt {attempt})')

	def _mark_failed(self, section: dict, state: dict, plan: dict) -> None:
		"""Mark section as failed after all retries"""
		section['status'] = 'failed'
		state['failed_sections'].append(section['id'])
		self._save_plan(plan)
		self._save_state(state)
		logger.error(f'  ✗ Section failed after {section.get("max_retries", 3)} attempts')

	def _export_paper(self, state: dict, plan: dict) -> None:
		"""Export completed paper to PDF and DOCX"""
		logger.info(f'\n{"=" * 60}')
		logger.info('EXPORTING PAPER')
		logger.info(f'{"=" * 60}\n')

		if self.export_engine is None:
			self.export_engine = ExportEngine(
				profile_name=self.current_profile.name,  # type: ignore
				output_dir=self.state_dir.parent / 'output',
			)

		try:
			metadata = {
				'topic': state['config']['topic'],
				'author': state['config'].get('author', 'Anonymous'),
				'abstract': self._generate_abstract(plan),
				'created_at': state['created_at'],
				'profile': self.current_profile.name,  # type: ignore
			}

			outputs = self.export_engine.export_paper(
				sections_dir=self.sections_dir,
				sources_db=self.research_agent.sources_db,
				metadata=metadata,
				formats=('pdf', 'docx'),
			)

			logger.info('✓ Export complete:')
			for fmt, path in outputs.items():
				logger.info(f'  - {fmt.upper()}: {path}')

			logger.info(f'\n{"=" * 60}\n')

		except Exception as e:
			logger.error(f'Export failed: {e}')
			logger.warning('Paper sections saved in markdown format in state/sections/')

	def _generate_abstract(self, plan: dict) -> str:
		intro_file = self.sections_dir / '00_introduction.md'
		methodology_files = list(self.sections_dir.glob('*methodology*.md')) + list(
			self.sections_dir.glob('*system_analysis*.md')
		)
		findings_files = (
			list(self.sections_dir.glob('*findings*.md'))
			+ list(self.sections_dir.glob('*results*.md'))
			+ list(self.sections_dir.glob('*implementation*.md'))
		)
		conclusion_files = list(self.sections_dir.glob('*conclusion*.md'))

		intro_text = intro_file.read_text()[:800] if intro_file.exists() else ''
		methodology_text = methodology_files[0].read_text()[:600] if methodology_files else ''
		findings_text = findings_files[0].read_text()[:600] if findings_files else ''
		conclusion_text = conclusion_files[0].read_text()[:600] if conclusion_files else ''

		# Generate abstract using LLM
		prompt = f"""Generate a 150-200 word academic abstract for this research paper.

	# Paper Topic
	{plan['topic']}

	# Introduction (excerpt)
	{intro_text}

	# Methodology (excerpt)
	{methodology_text}

	# Key Findings (excerpt)
	{findings_text}

	# Conclusion (excerpt)
	{conclusion_text}

	# Abstract Requirements
	- 150-200 words ONLY (strict limit)
	- Include: problem statement, methods, key findings, implications
	- Use past tense ("This research examined...", "Results showed...")
	- No citations in abstract
	- One paragraph, no bullet points
	- Professional academic tone

	Write ONLY the abstract, nothing else:"""

		try:
			abstract = self.llm_client.generate(prompt, max_tokens=300).strip()

			word_count = len(abstract.split())
			if word_count < 100:
				logger.warning(f'Abstract too short ({word_count} words), using fallback')
			elif word_count > 250:
				abstract = ' '.join(abstract.split()[:200]) + '...'

			return abstract

		except Exception as e:
			logger.error(f'Abstract generation failed: {e}')
			return ''

	def _setup_signal_handlers(self) -> None:
		def signal_handler(signum, frame):
			signal_name = signal.Signals(signum).name
			logger.warning(f'\n\n Received {signal_name} - saving progress...')
			self._interruption_requested = True

			if self._current_section_id is not None:
				logger.info(f'Finishing section {self._current_section_id} before exit...')

		signal.signal(signal.SIGINT, signal_handler)
		signal.signal(signal.SIGTERM, signal_handler)

	def _save_state(self, state: dict) -> None:
		state['updated_at'] = datetime.now(UTC).isoformat()
		with open(self.state_file, 'w') as f:
			json.dump(state, f, indent=2)

	def _load_state(self) -> dict:
		with open(self.state_file) as f:
			return json.load(f)

	def _save_plan(self, plan: dict) -> None:
		with open(self.plan_file, 'w') as f:
			json.dump(plan, f, indent=2)

	def _load_plan(self) -> dict:
		with open(self.plan_file) as f:
			return json.load(f)

	def _save_section_content(self, section_id: int, section_title: str, content: str) -> None:
		# Sanitize filename by replacing spaces and slashes
		safe_title = section_title.lower().replace(' ', '_').replace('/', '_')
		filename = f'{section_id:02d}_{safe_title}.md'
		filepath = self.sections_dir / filename
		with open(filepath, 'w') as f:
			f.write(f'# {section_title}\n\n{content}')

	def _load_section_content(self, section_id: int) -> str | None:
		files = list(self.sections_dir.glob(f'{section_id:02d}_*.md'))
		if not files:
			return None
		with open(files[0]) as f:
			lines = f.readlines()
			return ''.join(lines[2:]) if len(lines) > 2 else None

	def _generate_quality_report(self, plan: dict) -> None:
		metrics = {
			'total_sections': len(plan['sections']),
			'validated_sections': sum(1 for s in plan['sections'] if s['status'] == 'validated'),
			'total_words': sum(s.get('word_count', 0) for s in plan['sections']),
			'total_citations': sum(s.get('citations_count', 0) for s in plan['sections']),
			'avg_citations_per_section': 0.0,
			'sections_under_min_words': 0,
			'sections_over_max_words': 0,
			'sections_with_placeholders': 0,
		}

		if metrics['validated_sections'] > 0:
			metrics['avg_citations_per_section'] = metrics['total_citations'] / metrics['validated_sections']

		# Check word count compliance
		for section in plan['sections']:
			if section['status'] != 'validated':
				continue

			word_count = section.get('word_count', 0)
			min_words = section.get('min_words', 0)
			max_words = section.get('max_words', 1500)

			if word_count < min_words * 0.8:  # 20% under
				metrics['sections_under_min_words'] += 1
			if word_count > max_words * 1.2:  # 20% over
				metrics['sections_over_max_words'] += 1

		# Check for placeholder citations in saved sections
		import re

		for section_file in self.sections_dir.glob('*.md'):
			content = section_file.read_text()
			if re.search(r'\[source_?\w*\]', content, re.IGNORECASE):
				metrics['sections_with_placeholders'] += 1

		# Calculate estimated page count
		estimated_pages = metrics['total_words'] / 250  # ~250 words per page double-spaced

		# Generate report
		logger.info(f'\n{"=" * 60}')
		logger.info('QUALITY REPORT')
		logger.info(f'{"=" * 60}')
		logger.info(f'Total Sections: {metrics["total_sections"]}')
		logger.info(
			f'Validated: {metrics["validated_sections"]} ({
				metrics["validated_sections"] / metrics["total_sections"] * 100:.1f}%)'
		)
		logger.info(f'Total Words: {metrics["total_words"]:,}')
		logger.info(f'Estimated Pages: {estimated_pages:.0f}')
		logger.info(f'Total Citations: {metrics["total_citations"]}')
		logger.info(f'Avg Citations/Section: {metrics["avg_citations_per_section"]:.1f}')

		# Warnings
		if metrics['sections_under_min_words'] > 0:
			logger.warning(f'{metrics["sections_under_min_words"]} sections under word count')

		if metrics['sections_over_max_words'] > 0:
			logger.warning(f'{metrics["sections_over_max_words"]} sections over word count')

		if metrics['sections_with_placeholders'] > 0:
			logger.error(f'{metrics["sections_with_placeholders"]} sections contain placeholder citations!')
			logger.error('Review and fix before export.')

		if estimated_pages > 60:
			logger.warning(f'Paper is {estimated_pages:.0f} pages (consider reducing word counts)')

		logger.info(f'{"=" * 60}\n')

		# Save metrics to file
		import json

		metrics_file = self.state_dir / 'quality_metrics.json'
		with open(metrics_file, 'w') as f:
			json.dump(metrics, f, indent=2)

		logger.info(f'Quality metrics saved to: {metrics_file}')


if __name__ == '__main__':
	input_data = {
		'topic': 'transformer neural networks',
		'template': ['Introduction', 'Methodology'],
	}

	orchestrator = Orchestrator(state_dir='state')
	orchestrator.initialize(input_data)
	orchestrator.run()
