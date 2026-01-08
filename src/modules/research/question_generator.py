import json
import re
from datetime import UTC, datetime

from src.models import Question, ResearchPlan
from src.utils.llm_client import UnifiedLLMClient


class ResearchQuestionGenerator:
	def __init__(self, llm_client: UnifiedLLMClient, max_retries: int = 3):
		self.llm_client = llm_client
		self.max_retries = max_retries

	def generate_plan(self, topic: str, sections: list[str], num_questions: int = 15) -> ResearchPlan:
		attempts = 0
		final_questions = []
		is_approved = False

		while not is_approved and attempts < self.max_retries:
			attempts += 1
			print(f'\n[Attempt {attempts}] Generating research questions...')

			prompt = self._build_prompt(topic, sections, num_questions)
			raw_response = self.llm_client.generate(prompt)

			try:
				final_questions = self._parse_json_to_questions(raw_response, num_questions, sections)
				final_questions, is_approved = self.approve_questions(final_questions, sections)
			except (json.JSONDecodeError, KeyError, ValueError) as e:
				print(f'Error parsing LLM response: {e}. Retrying...')
				continue

		if not is_approved:
			print('\n[!] Maximum regeneration attempts reached. Please enter questions manually.')
			final_questions = self._manual_entry(sections)

		return ResearchPlan(
			topic=topic, questions=final_questions, total_sources=0, completed_at=datetime.now(UTC).isoformat()
		)

	def _build_prompt(self, topic: str, template: list[str], num_questions: int) -> str:
		total_sections = len(template)
		section_list = '\n'.join([f'ID {i}: {title}' for i, title in enumerate(template)])

		early_bound = max(0, total_sections // 3)
		late_bound = min(total_sections - 1, (2 * total_sections) // 3)

		return f"""You are a senior academic supervisor. 
    Assign exactly {num_questions} research questions for the following paper.

    TOPIC: "{topic}"

    PAPER STRUCTURE:
    {section_list}

    STRICT CONSTRAINTS:
    1. QUANTITY: You must generate EXACTLY {num_questions} questions. No more, no less.
    2. DISTRIBUTION: Ensure the questions cover the entire scope of the paper:
    - CONTEXTUAL: At least one question focusing on the foundations, problem statement, or 
    existing literature (Target IDs: 0 to {early_bound}).
    - ANALYTICAL: At least two questions focusing on the core investigation, methodology, or 
    specific analysis (Target IDs: {early_bound + 1} to {late_bound}).
    - SYNTHESIS: At least one question focusing on implications, future directions, or 
    conclusions (Target IDs: {late_bound + 1} to {total_sections - 1}).
    3. FORMAT: Return ONLY a JSON object. No conversational text or markdown blocks.
    4. QUALITY: Questions must be specific, evidence-based, and analytical 
    (asking "How" or "To what extent" rather than simple "What" questions).

    REQUIRED JSON STRUCTURE:
    {{
    "questions": [
        {{
        "text": "The analytical question here?",
        "target_sections": [integer_ids] 
        }}
    ]
    }}

    Generate the {num_questions} questions now:"""

	def _parse_json_to_questions(self, text: str, expected_count: int, template: list[str]) -> list[Question]:
		# 1. Extract JSON
		json_match = re.search(r'(\{.*\})', text, re.DOTALL)
		clean_text = json_match.group(1) if json_match else text
		data = json.loads(clean_text)

		raw_questions = data.get('questions', [])

		# 2. Safety Slice: Ensure we don't exceed the requested count
		if len(raw_questions) > expected_count:
			raw_questions = raw_questions[:expected_count]

		processed_questions = []
		for i, q_data in enumerate(raw_questions):
			text = q_data.get('text', '')
			raw_targets = q_data.get('target_sections', [])

			# 3. Normalization Logic: Convert Section Names to IDs if necessary
			normalized_targets = []
			for target in raw_targets:
				if isinstance(target, int):
					if 0 <= target < len(template):
						normalized_targets.append(target)
				elif isinstance(target, str):
					try:
						idx = [t.lower() for t in template].index(target.lower())
						normalized_targets.append(idx)
					except ValueError:
						if target.isdigit():
							normalized_targets.append(int(target))

			processed_questions.append(
				Question(
					question_id=f'RQ-{i + 1:02d}',
					text=text,
					target_sections=list(set(normalized_targets)),  # Unique IDs
				)
			)

		return processed_questions

	def approve_questions(self, questions: list[Question], template: list[str]) -> tuple[list[Question], bool]:
		for idx, q in enumerate(questions, 1):
			valid_sections = [template[i] for i in q.target_sections if i < len(template)]
			print(f'\n{idx}. {q.text}')
			print(f'   Target Sections: {", ".join(valid_sections)}')

		print('\n' + '=' * 60)
		response = input('\nApprove? (y)es / (e)dit / (r)egenerate: ').lower()

		if response == 'y':
			return questions, True
		elif response == 'e':
			return self._edit_questions(questions, template), True
		return questions, False

	def _edit_questions(self, questions: list[Question], template: list[str]) -> list[Question]:
		edited_list = []
		print('\n--- Editing Mode ---')
		for q in questions:
			print(f'\nCurrent: {q.text}')
			new_text = input('New text (leave blank to keep): ').strip()

			print(f'Current Sections: {q.target_sections}')
			new_sections_input = input('New section IDs (comma-separated, leave blank to keep): ').strip()

			text = new_text if new_text else q.text
			target_sections = q.target_sections
			if new_sections_input:
				try:
					target_sections = [int(x.strip()) for x in new_sections_input.split(',')]
				except ValueError:
					print('Invalid IDs, keeping original.')

			edited_list.append(Question(question_id=q.question_id, text=text, target_sections=target_sections))
		return edited_list

	def _manual_entry(self, template: list[str]) -> list[Question]:
		questions = []
		count = int(input('How many questions would you like to add manually? '))
		for i in range(count):
			text = input(f'Question {i + 1} text: ')
			print(f'Sections: {[f"{i}:{t}" for i, t in enumerate(template)]}')
			secs = input('Target section IDs (comma separated): ')
			target_ids = [int(x.strip()) for x in secs.split(',')]
			questions.append(Question(question_id=f'RQ-{i + 1:02d}', text=text, target_sections=target_ids))
		return questions


if __name__ == '__main__':
	from openai import OpenAI

	from src.config.settings import settings

	raw_client = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=settings.OPENROUTER_API_KEY)

	llm_client = UnifiedLLMClient(
		client=raw_client,
		model='xiaomi/mimo-v2-flash:free',
		site_url='https://github.com/DanielPopoola/scholarly',
		app_name='Scholarly Test Suite',
	)

	RG = ResearchQuestionGenerator(llm_client)
	topic = "Rethinking Women's Bodily Autonomy In Nigerian Healthcare: A feminist legal theory analysis"
	sections = [
		'Introduction',
		'Statement of Research problem',
		'Research Objectives',
		'Key concepts in Literature',
		'Methodology',
		'Key findings',
		'Conclusion',
	]
	questions = RG.generate_plan(topic, sections, num_questions=8)
