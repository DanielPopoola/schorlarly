DEFAULT_CONSTRAINTS = {
	'max_section_word_count': 1500,
	'min_citations_per_section': 3,
	'max_time_per_section_minutes': 20,
}


DEFAULT_STYLE = {
	'tone': 'professional',
	'citation_format': 'APA',
	'complexity': 'undergraduate',
	'additional_instructions': None,
}


VALID_TONES = ['professional', 'formal', 'conversational']
VALID_CITATION_FORMATS = ['APA', 'Harvard', 'MLA', 'Chicago']
VALID_COMPLEXITY_LEVELS = ['undergraduate', 'graduate', 'expert']
