from typing import Any

from config.defaults import (
	DEFAULT_CONSTRAINTS,
	DEFAULT_STYLE,
	VALID_CITATION_FORMATS,
	VALID_COMPLEXITY_LEVELS,
	VALID_TONES,
)


class ValidationError(Exception):
	pass


class InputValidator:
	def validate(self, raw_input: dict[str, Any]) -> dict[str, Any]:
		self._validate_required_fields(raw_input)

		topic = self._validate_topic(raw_input['topic'])
		template = self._validate_template(raw_input['template'])
		constraints = self._validate_constraints(raw_input.get('constraints', {}))
		style = self._validate_style(raw_input.get('style', {}))

		return {
			'topic': topic,
			'template': template,
			'constraints': constraints,
			'style': style,
		}

	def _validate_required_fields(self, data: dict) -> None:
		if 'topic' not in data:
			raise ValidationError("Missing required field: 'topic'")
		if 'template' not in data:
			raise ValidationError("Missing required field: 'template'")

	def _validate_topic(self, topic: Any) -> str:
		if not isinstance(topic, str):
			raise ValidationError("'topic' must be a string")

		topic = topic.strip()
		if not topic:
			raise ValidationError("'topic' cannot be empty")

		if len(topic) < 10:
			raise ValidationError("'topic' is too short (minimum 10 characters)")

		return topic

	def _validate_template(self, template: Any) -> list[str]:
		if not isinstance(template, list):
			raise ValidationError("'template' must be a list of section names")

		if len(template) == 0:
			raise ValidationError("'template' cannot be empty")

		if len(template) > 40:
			raise ValidationError("'template' has too many sections (maximum 20)")

		validated_sections = []
		for i, section in enumerate(template):
			if not isinstance(section, str):
				raise ValidationError(f'Section {i} must be a string')

			section = section.strip()
			if not section:
				raise ValidationError(f'Section {i} cannot be empty')

			validated_sections.append(section)

		return validated_sections

	def _validate_constraints(self, constraints: dict) -> dict:
		result = DEFAULT_CONSTRAINTS.copy()

		for key, value in constraints.items():
			if key not in DEFAULT_CONSTRAINTS:
				raise ValidationError(f"Unknown constraint: '{key}'")

			if not isinstance(value, int):
				raise ValidationError(f"Constraint '{key}' must be an integer")

			if value <= 0:
				raise ValidationError(f"Constraint '{key}' must be positive")

			result[key] = value

		return result

	def _validate_style(self, style: dict) -> dict:
		result = DEFAULT_STYLE.copy()

		if 'tone' in style:
			tone = style['tone']
			if tone not in VALID_TONES:
				raise ValidationError(f"Invalid tone '{tone}'. Must be one of: {', '.join(VALID_TONES)}")
			result['tone'] = tone

		if 'citation_format' in style:
			fmt = style['citation_format']
			if fmt not in VALID_CITATION_FORMATS:
				raise ValidationError(
					f"Invalid citation_format '{fmt}'. Must be one of: {', '.join(VALID_CITATION_FORMATS)}"
				)
			result['citation_format'] = fmt

		if 'complexity' in style:
			complexity = style['complexity']
			if complexity not in VALID_COMPLEXITY_LEVELS:
				raise ValidationError(
					f"Invalid complexity '{complexity}'. Must be one of: {', '.join(VALID_COMPLEXITY_LEVELS)}"
				)
			result['complexity'] = complexity

		if 'additional_instructions' in style:
			result['additional_instructions'] = style['additional_instructions']

		return result
