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
		'Introduction': Section(SectionType.INTRO_CONCLUSION, 3, 400, 800),
		'Statement of the Problem': Section(SectionType.INTRO_CONCLUSION, 2, 300, 500),
		'Objective of the Study': Section(SectionType.INTRO_CONCLUSION, 1, 200, 400),
		'Significance': Section(SectionType.INTRO_CONCLUSION, 2, 200, 400),
		'Scope of the Study': Section(SectionType.INTRO_CONCLUSION, 0, 200, 400),
		'Limitations': Section(SectionType.INTRO_CONCLUSION, 0, 150, 300),
		'Organization of the Study': Section(SectionType.INTRO_CONCLUSION, 0, 100, 200),
		'Definition of Terms': Section(SectionType.INTRO_CONCLUSION, 2, 150, 300),
		'Conclusion': Section(SectionType.INTRO_CONCLUSION, 1, 300, 600),
		'Recommendations': Section(SectionType.INTRO_CONCLUSION, 1, 200, 400),
	}


def build_profiles():
	base = get_base_sections()

	estam = base | {
		'Background to the Study': Section(SectionType.LITERATURE, 6, 600, 1000),
		'Conceptual Framework': Section(SectionType.LITERATURE, 5, 400, 800),
		'Theoretical Framework': Section(SectionType.LITERATURE, 5, 600, 1000),
		'Empirical studies': Section(SectionType.LITERATURE, 8, 1000, 1800, research_strategy='targeted'),
		'Appraisal': Section(SectionType.LITERATURE, 4, 300, 600),
		'Research Design': Section(SectionType.METHODOLOGY, 3, 300, 600),
		'Population of the Study': Section(SectionType.METHODOLOGY, 1, 200, 400),
		'Sample and Sampling Techniques': Section(SectionType.METHODOLOGY, 2, 300, 600),
		'Instrument for Data Collection': Section(SectionType.METHODOLOGY, 2, 300, 600),
		'Validity of the Instrument': Section(SectionType.METHODOLOGY, 3, 300, 400),
		'Reliability of the Instrument': Section(SectionType.METHODOLOGY, 3, 200, 400),
		'Procedure for Data Collection': Section(SectionType.METHODOLOGY, 2, 300, 600),
		'Method of Data Analysis': Section(SectionType.METHODOLOGY, 3, 300, 600),
		'Answers to Research Questions': Section(SectionType.TECHNICAL, 4, 600, 1200, requires_diagrams=True),
		'Testing of Hypotheses': Section(SectionType.TECHNICAL, 4, 600, 1200),
		'Summary of the Findings': Section(SectionType.INTRO_CONCLUSION, 0, 100, 200),
		'Discussion of the Findings': Section(SectionType.DISCUSSION, 6, 1000, 1800),
		'Implications of the Study': Section(SectionType.DISCUSSION, 3, 400, 800),
	}

	cs_eng = base | {
		'Existing Approach to Problem Identified': Section(SectionType.LITERATURE, 6, 600, 1000),
		'Effort to counter/solve existing challenges': Section(SectionType.LITERATURE, 5, 300, 600),
		'Specific Approach to Problem Identified': Section(SectionType.METHODOLOGY, 0, 400, 800),
		'System Analysis': Section(SectionType.TECHNICAL, 3, 600, 1000, requires_diagrams=True),
		'Method of Data Collection': Section(SectionType.METHODOLOGY, 0, 200, 400),
		'Problem of the Current System': Section(SectionType.TECHNICAL, 2, 300, 600),
		'Objective of the new system': Section(SectionType.INTRO_CONCLUSION, 0, 200, 400),
		'Menu Specification': Section(SectionType.TECHNICAL, 1, 200, 400),
		'Overview of the System Flowchart': Section(SectionType.TECHNICAL, 2, 300, 600, requires_diagrams=True),
		'Procedural Flowchart': Section(SectionType.TECHNICAL, 2, 300, 600, requires_diagrams=True),
		'System Design': Section(SectionType.TECHNICAL, 2, 800, 1200, requires_diagrams=True),
		'System Implementation': Section(SectionType.IMPLEMENTATION, 1, 600, 1000, requires_code=True),
		'System Requirement': Section(SectionType.IMPLEMENTATION, 0, 100, 200),
		'Hardware Requirement': Section(SectionType.IMPLEMENTATION, 0, 100, 200),
		'Software Requirement': Section(SectionType.IMPLEMENTATION, 0, 100, 200),
		'Test-Run': Section(SectionType.IMPLEMENTATION, 1, 400, 800, requires_code=True),
		'Program Documentation': Section(SectionType.IMPLEMENTATION, 1, 300, 600, requires_code=True),
		'User Manual': Section(SectionType.IMPLEMENTATION, 0, 400, 800),
		'System Maintenance': Section(SectionType.IMPLEMENTATION, 0, 200, 400),
	}

	return {'management': Profile('management', estam), 'engineering': Profile('engineering', cs_eng)}


class ProfileManager:
	def __init__(self):
		self.profiles = build_profiles()

	def detect(self, headings: list[str]) -> Profile:
		corpus = ' '.join(headings).lower()
		cs_sigs = ['system analysis', 'flowchart', 'test-run', 'manual', 'changeover']
		return self.profiles['engineering'] if any(s in corpus for s in cs_sigs) else self.profiles['management']

	def get(self, name: str) -> Profile:
		return self.profiles.get(name, self.profiles['management'])
