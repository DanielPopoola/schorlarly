from dataclasses import dataclass
from enum import Enum, auto


class SectionType(Enum):
	INTRO_CONCLUSION = auto()
	LITERATURE = auto()
	TECHNICAL = auto()
	METHODOLOGY = auto()
	IMPLEMENTATION = auto()
	DISCUSSION = auto()


@dataclass(frozen=True)
class Section:
	type: SectionType
	min_citations: int = 0
	min_word_count: int = 400
	max_word_count: int = 1500
	requires_code: bool = False
	requires_diagrams: bool = False
	research_strategy: str = 'global'


class Profile:
	def __init__(self, name: str, sections: dict):
		self.name, self.sections = name, sections

	def get_section(self, title: str) -> Section:
		t = title.lower()
		return next((v for k, v in self.sections.items() if k.lower() in t), Section(SectionType.DISCUSSION, 4))


def get_base_sections():
	return {
		'Introduction': Section(SectionType.INTRO_CONCLUSION, 3, 500),
		'Statement of the Problem': Section(SectionType.INTRO_CONCLUSION, 2, 400, 600),
		'Objective of the Study': Section(SectionType.INTRO_CONCLUSION, 1, 300, 500),
		'Significance': Section(SectionType.INTRO_CONCLUSION, 2, 300, 500),
		'Scope of the Study': Section(SectionType.INTRO_CONCLUSION, 0, 300, 500),
		'Definition of Terms': Section(SectionType.INTRO_CONCLUSION, 2, 200, 400),
		'Conclusion': Section(SectionType.INTRO_CONCLUSION, 1, 400, 800),
		'Recommendations': Section(SectionType.INTRO_CONCLUSION, 1, 300, 600),
	}


def build_profiles():
	base = get_base_sections()

	estam = base | {
		'Background': Section(SectionType.LITERATURE, 6, 800),
		'Conceptual Framework': Section(SectionType.LITERATURE, 5, 600),
		'Theoretical Framework': Section(SectionType.LITERATURE, 5, 800),
		'Empirical studies': Section(SectionType.LITERATURE, 8, 1500, 3000, research_strategy='targeted'),
		'Appraisal': Section(SectionType.LITERATURE, 4),
		'Research Design': Section(SectionType.METHODOLOGY, 3),
		'Population of the Study': Section(SectionType.METHODOLOGY, 1, 300),
		'Sample and Sampling Techniques': Section(SectionType.METHODOLOGY, 2),
		'Instrument for Data Collection': Section(SectionType.METHODOLOGY, 2, 500),
		'Validity of the Instrument': Section(SectionType.METHODOLOGY, 3, 300),
		'Reliability of the Instrument': Section(SectionType.METHODOLOGY, 3, 300),
		'Procedure for Data Collection': Section(SectionType.METHODOLOGY),
		'Method of Data Analysis': Section(SectionType.METHODOLOGY, 3),
		'Answers to Research xQuestions': Section(SectionType.TECHNICAL, requires_diagrams=True),
		'Testing of Hypotheses': Section(SectionType.TECHNICAL),
		'Discussion of the Findings': Section(SectionType.DISCUSSION, 6, 1500, 2500),
		'Implications of the Study': Section(SectionType.DISCUSSION, 3, 500),
	}

	cs_eng = base | {
		'Existing Approach': Section(SectionType.LITERATURE, 6, 1000),
		'Specific Approach': Section(SectionType.METHODOLOGY, 3, 600),
		'System Analysis': Section(SectionType.TECHNICAL, 3, 800, requires_diagrams=True),
		'Current System': Section(SectionType.TECHNICAL),
		'Menu Specification': Section(SectionType.TECHNICAL),
		'Flowchart': Section(SectionType.TECHNICAL, requires_diagrams=True),
		'System Design': Section(SectionType.TECHNICAL, 2, 1000, requires_diagrams=True),
		'Implementation': Section(SectionType.IMPLEMENTATION, 1, 800, requires_code=True),
		'Requirement': Section(SectionType.IMPLEMENTATION),
		'Test-Run': Section(SectionType.IMPLEMENTATION, requires_code=True),
		'Program Documentation': Section(SectionType.IMPLEMENTATION, requires_code=True),
		'User Manual': Section(SectionType.IMPLEMENTATION),
		'Maintenance': Section(SectionType.IMPLEMENTATION),
	}

	return {'management': Profile('management', estam), 'engineering': Profile('engineering', cs_eng)}


class ProfileManager:
	def __init__(self):
		self.profiles = build_profiles()

	def detect(self, headings: list[str]) -> Profile:
		corpus = ' '.join(headings).lower()
		cs_sigs = ['system analysis', 'flowchart', 'test-run', 'manual', 'changeover']
		return self.profiles['engineering'] if any(s in corpus for s in cs_sigs) else self.profiles['management']
