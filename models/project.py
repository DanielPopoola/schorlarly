from dataclasses import dataclass
from enum import Enum


class ProjectType(Enum):
	EMPIRICAL = 'empirical'
	COMPUTATIONAL = 'computational'
	REVIEW = 'review'
	PROPOSAL = 'proposal'


class ArtifactType(Enum):
	DATASET = 'dataset'
	CODEBASE = 'codebase'
	SIMULATION_RESULTS = 'simulation_results'
	SURVEY_INSTRUMENT = 'survey_instrument'
	EXPERIMENTAL_PROCEDURE = 'experimental_procedure'


@dataclass(frozen=True)
class Artifact:
	id: str
	type: ArtifactType
	description: str
	file_path: str | None = None
	url: str | None = None
