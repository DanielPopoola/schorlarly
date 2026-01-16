import logging
from typing import Any

from src.core.config_loader import SectionConfig
from src.core.context_manager import SectionContext
from src.generators.base import BaseGenerator
from src.parsers.input_parser import ProjectInput

logger = logging.getLogger(__name__)


class InteractiveSectionGenerator(BaseGenerator):
	SECTION_QUESTIONS = {
		'Introduction': [
			'What is the main topic/problem your project addresses?',
			'Why is this topic important or relevant?',
			'What gap or need does your project fill?',
		],
		'Statement of the Problem': [
			'What specific problem does your project solve?',
			'Who is affected by this problem?',
			'What are the consequences of not solving this problem?',
			'What makes this problem challenging?',
		],
		'Objective of the Study': [
			'What are the main goals of your project?',
			'What specific outcomes do you want to achieve?',
			'What will success look like?',
		],
		'Significance of the Study': [
			'Who will benefit from your project?',
			'How will your project impact the field/users?',
			'What contributions does your work make?',
		],
		'Scope of the Study': [
			'What does your project cover?',
			'What is NOT included in your project?',
			'What are the boundaries of your work?',
		],
		'Limitations': [
			'What limitations did you face?',
			'What constraints affected your work?',
			'What could not be achieved and why?',
		],
		'Specific Approach to Problem Identified': [
			'What specific approach/methodology did you use?',
			'Why did you choose this approach over alternatives?',
			'How does your approach differ from existing solutions?',
		],
		'Method of Data Collection': [
			'How did you gather requirements/data?',
			'What methods did you use (surveys, interviews, etc)?',
			'Who did you collect data from?',
		],
		'Problem of the Current System': [
			'What are the main issues with the current/existing system?',
			'What complaints or pain points exist?',
			'What inefficiencies did you identify?',
		],
		'Objective of the new system': [
			'What will your new system accomplish?',
			'What improvements will it bring?',
			'What problems will it solve?',
		],
		'System Maintenance': [
			'How will your system be maintained?',
			'What updates or modifications might be needed?',
			'What maintenance procedures should be followed?',
		],
	}

	def generate(
		self, section_config: SectionConfig, user_input: ProjectInput | None, context: dict[str, Any]
	) -> SectionContext:
		logger.info(f'Generating interactive section: {section_config.name}')

		user_content = self._extract_user_content(section_config.name, user_input, context)

		if not user_content or len(user_content) < 200:
			logger.info(f'Insufficient input for {section_config.name}, asking user...')
			user_content = self._ask_user(section_config.name)

		base_prompt = self._build_base_prompt(section_config, context)
		interactive_prompt = self._build_interactive_prompt(section_config, user_content)

		full_prompt = base_prompt + interactive_prompt

		content_raw = self.llm_client.generate(
			full_prompt, temperature=0.7, max_tokens=section_config.word_count['max'] * 2
		)

		content, key_points = self._parse_combined_response(content_raw)

		valid, word_count = self._validate_word_count(
			content, section_config.word_count['min'], section_config.word_count['max']
		)

		if not valid:
			content = self._adjust_content_length(
				content, section_config.word_count['min'], section_config.word_count['max'], section_config.name
			)
			word_count = self._count_words(content)
			# Re-extract key points if content changed significantly
			_, key_points = self._parse_combined_response(content)

		citations = self._extract_citations(content)

		logger.info(f'Generated {word_count} words')

		return SectionContext(
			name=section_config.name,
			content=content,
			key_points=key_points,
			citations=citations,
			word_count=word_count,
			terms_defined=[],
		)

	def _extract_user_content(self, section_name: str, user_input: ProjectInput | None, context: dict[str, Any]) -> str:
		if not user_input:
			return ''

		name_lower = section_name.lower()

		if 'introduction' in name_lower:
			return f'{user_input.problem_statement}\n\n{user_input.solution}'

		elif 'statement' in name_lower and 'problem' in name_lower:
			return user_input.problem_statement

		elif 'objective' in name_lower:
			return user_input.solution

		elif 'significance' in name_lower:
			return f'{user_input.solution}\n\nDomain: {user_input.domain}'

		elif 'scope' in name_lower:
			return user_input.solution

		elif 'limitation' in name_lower:
			return user_input.approach_justification

		elif 'specific approach' in name_lower:
			return f'{user_input.approach_justification}\n\n{user_input.system_architecture}'

		elif 'method' in name_lower and 'data' in name_lower:
			return ''

		elif 'problem' in name_lower and 'current' in name_lower:
			return user_input.problem_statement

		elif 'objective' in name_lower and 'new' in name_lower:
			return user_input.solution

		elif 'maintenance' in name_lower:
			return ''

		return ''

	def _ask_user(self, section_name: str) -> str:
		questions = self.SECTION_QUESTIONS.get(section_name, [])

		if not questions:
			print(f'\nSection: {section_name}')
			print('Please provide content for this section:')
			user_response = input('> ')
			return user_response

		print(f'\nSection: {section_name}')
		print('Please answer the following questions:\n')

		answers = []
		for i, question in enumerate(questions, 1):
			print(f'{i}. {question}')
			answer = input('> ')
			answers.append(f'Q: {question}\nA: {answer}')

		return '\n\n'.join(answers)

	def _build_interactive_prompt(self, section_config: SectionConfig, user_content: str) -> str:
		name_lower = section_config.name.lower()

		if 'introduction' in name_lower:
			focus = """Write an Introduction that:
- Introduces the topic and its context
- States why the topic is important
- Previews what the paper will cover
- Engages the reader

This is the opening of the paper - make it compelling but academic."""

		elif 'statement' in name_lower and 'problem' in name_lower:
			focus = """Write a Statement of the Problem that:
- Clearly defines the specific problem
- Explains who is affected
- Describes the consequences of the problem
- Makes the problem concrete and specific"""

		elif 'objective' in name_lower and 'study' in name_lower:
			focus = """Write the Objective of the Study that:
- States clear, specific goals
- Uses measurable outcomes where possible
- Aligns with the problem statement
- Shows what the project aims to accomplish"""

		elif 'significance' in name_lower:
			focus = """Write the Significance of the Study that:
- Explains the impact and importance
- Identifies beneficiaries
- Describes contributions to the field
- Justifies why this work matters"""

		elif 'scope' in name_lower:
			focus = """Write the Scope of the Study that:
- Defines boundaries of the work
- States what IS included
- States what is NOT included
- Sets clear expectations"""

		elif 'limitation' in name_lower:
			focus = """Write the Limitations section that:
- Honestly describes constraints
- Explains factors beyond your control
- Discusses resource/time limitations
- Shows awareness of project boundaries"""

		elif 'specific approach' in name_lower:
			focus = """Write about your Specific Approach that:
- Describes your methodology in detail
- Justifies why you chose this approach
- Compares to alternatives
- Explains how it solves the problem"""

		else:
			focus = f'Write the {section_config.name} section based on the information provided.'

		prompt = f"""{focus}

USER INPUT:
{user_content}

Write the section now.

After writing, extract 3-5 KEY POINTS in this format:

---KEY_POINTS---
- First key insight
- Second key insight
..."""

		return prompt
