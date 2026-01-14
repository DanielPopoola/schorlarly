import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class SectionConfig:
	name: str
	type: str
	word_count: dict[str, int]
	depends_on: list[str]
	research: dict[str, Any] | None = None
	code_required: bool = False


class ConfigLoader:
	def __init__(self, config_dir: str = 'config'):
		load_dotenv()
		self.config_dir = Path(config_dir)
		self.settings = self._load_settings()
		self.template = self._load_template()

	def _load_settings(self) -> dict[str, Any]:
		settings_path = self.config_dir / 'settings.yaml'

		if not settings_path.exists():
			raise FileNotFoundError(f'Settings file not found: {settings_path}')

		with open(settings_path) as f:
			settings = yaml.safe_load(f)

		settings = self._inject_env_vars(settings)

		return settings

	def _load_template(self) -> dict[str, Any]:
		template_name = self.settings.get('active_template', 'final_year_project')
		template_path = self.config_dir / 'templates' / f'{template_name}.yaml'

		if not template_path.exists():
			raise FileNotFoundError(f'Template not found: {template_path}')

		with open(template_path) as f:
			template = yaml.safe_load(f)

		return template

	def _inject_env_vars(self, config: dict[str, Any]) -> dict[str, Any]:
		def replace_env(obj):
			if isinstance(obj, dict):
				new_obj = {}
				for key, value in obj.items():
					if key.endswith('_env') and isinstance(value, str):
						# Get env variable and create new key without _env suffix
						env_value = os.getenv(value)
						if not env_value:
							raise ValueError(f'Environment variable {value} not found')
						new_key = key.replace('_env', '')
						new_obj[new_key] = env_value
					else:
						new_obj[key] = replace_env(value)
				return new_obj
			elif isinstance(obj, list):
				return [replace_env(item) for item in obj]
			return obj

		return replace_env(config)  # type: ignore

	def get_sections(self) -> list[SectionConfig]:
		sections = []
		for section_data in self.template['sections']:
			sections.append(SectionConfig(**section_data))
		return sections

	def get_section(self, name: str) -> SectionConfig:
		for section_data in self.template['sections']:
			if section_data['name'] == name:
				return SectionConfig(**section_data)
		raise ValueError(f'Section not found: {name}')

	def get_llm_config(self) -> dict[str, Any]:
		return self.settings['llm']

	def get_research_config(self) -> dict[str, Any]:
		return self.settings['research']

	def get_citation_config(self) -> dict[str, Any]:
		return self.settings['citation']

	def get_writing_config(self) -> dict[str, Any]:
		return self.settings['writing']

	def get_output_config(self) -> dict[str, Any]:
		return self.settings['output']


# Singleton instance
_config = None


def get_config() -> ConfigLoader:
	global _config
	if _config is None:
		_config = ConfigLoader()
	return _config
