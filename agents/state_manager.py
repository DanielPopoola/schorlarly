import json
from datetime import datetime
from pathlib import Path
from typing import Any


class StateManager:
	def __init__(self, state_dir: Path):
		self.state_dir = state_dir
		self.state_file = state_dir / 'state.json'
		self.plan_file = state_dir / 'plan.json'
		self.checkpoint_file = state_dir / 'checkpoint.json'
		self.context_cache_file = state_dir / 'context_cache.json'

	def can_resume(self) -> bool:
		return self.state_file.exists() and self.plan_file.exists() and self.checkpoint_file.exists()

	def load_checkpoint(self) -> dict[str, Any]:
		with open(self.checkpoint_file) as f:
			checkpoint = json.load(f)

		with open(self.state_file) as f:
			state = json.load(f)

		with open(self.plan_file) as f:
			plan = json.load(f)

		# Load context cache if exists
		context_cache = {}
		if self.context_cache_file.exists():
			with open(self.context_cache_file) as f:
				context_cache = json.load(f)

		return {'checkpoint': checkpoint, 'state': state, 'plan': plan, 'context_cache': context_cache}

	def save_checkpoint(
		self, current_section_id: int, completed_sections: list[int], context_summaries: dict[int, str]
	) -> None:
		checkpoint = {
			'current_section_id': current_section_id,
			'completed_sections': completed_sections,
			'last_checkpoint': datetime.now().isoformat(),
			'can_resume': True,
		}

		# Atomic write (write to temp, then rename)
		temp_file = self.checkpoint_file.with_suffix('.tmp')
		with open(temp_file, 'w') as f:
			json.dump(checkpoint, f, indent=2)
		temp_file.replace(self.checkpoint_file)

		# Save context cache
		if context_summaries:
			temp_cache = self.context_cache_file.with_suffix('.tmp')
			with open(temp_cache, 'w') as f:
				json.dump(context_summaries, f, indent=2)
			temp_cache.replace(self.context_cache_file)

	def clear_checkpoint(self) -> None:
		if self.checkpoint_file.exists():
			self.checkpoint_file.unlink()
		if self.context_cache_file.exists():
			self.context_cache_file.unlink()
