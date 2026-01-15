import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class SectionStatus(Enum):
	PENDING = 'pending'
	IN_PROGRESS = 'in_progress'
	COMPLETED = 'completed'
	FAILED = 'failed'


class StateManager:
	def __init__(self, project_name: str, state_dir: Path):
		self.project_name = project_name
		self.state_file = state_dir / f'{project_name}_state.json'
		self.state_dir = Path(state_dir)

		self.section_status: dict[str, str] = {}
		self.metadata: dict[str, Any] = {
			'project_name': project_name,
			'created_at': None,
			'last_updated': None,
			'current_section': None,
		}

		if self.state_file.exists():
			self.load()
		else:
			self.metadata['created_at'] = datetime.now().isoformat()

	def initialize_sections(self, section_names: list[str]):
		for name in section_names:
			if name not in self.section_status:
				self.section_status[name] = SectionStatus.PENDING.value
		self.save()

	def set_section_status(self, section_name: str, status: SectionStatus):
		self.section_status[section_name] = status.value
		self.metadata['last_updated'] = datetime.now().isoformat()

		if status == SectionStatus.IN_PROGRESS:
			self.metadata['current_section'] = section_name
		elif status == SectionStatus.COMPLETED:
			self.metadata['current_section'] = self._get_next_pending()

		self.save()

	def get_section_status(self, section_name: str) -> SectionStatus:
		status_str = self.section_status.get(section_name, SectionStatus.PENDING.value)
		return SectionStatus(status_str)

	def _get_next_pending(self) -> str | None:
		for section_name, status in self.section_status.items():
			if status == SectionStatus.PENDING.value:
				return section_name
		return None

	def get_progress(self) -> dict[str, Any]:
		total = len(self.section_status)
		completed = sum(1 for s in self.section_status.values() if s == SectionStatus.COMPLETED.value)
		failed = sum(1 for s in self.section_status.values() if s == SectionStatus.FAILED.value)

		return {
			'total_sections': total,
			'completed': completed,
			'failed': failed,
			'remaining': total - completed - failed,
			'progress_percentage': (completed / total * 100) if total > 0 else 0,
			'current_section': self.metadata['current_section'],
		}

	def is_complete(self) -> bool:
		return all(status == SectionStatus.COMPLETED.value for status in self.section_status.values())

	def save(self):
		self.state_dir.mkdir(parents=True, exist_ok=True)

		state = {
			'metadata': self.metadata,
			'section_status': self.section_status,
		}

		with open(self.state_file, 'w') as f:
			json.dump(state, f, indent=2)

	def load(self):
		with open(self.state_file) as f:
			state = json.load(f)

		self.metadata = state['metadata']
		self.section_status = state['section_status']

	def reset(self):
		self.section_status.clear()
		self.metadata['current_section'] = None
		self.metadata['last_updated'] = datetime.now().isoformat()
		self.save()
