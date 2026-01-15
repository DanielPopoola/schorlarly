"""
Quick test to verify configuration loads correctly.
"""

from src.core.config_loader import get_config


def test_config_loading():
	"""Test that all configs load without errors."""
	config = get_config()

	print('Testing configuration loading...\n')

	# Test settings
	llm_config = config.get_llm_config()
	print(f'✓ LLM Provider: {llm_config["provider"]}')
	print(f'✓ LLM Model: {llm_config["model"]}')

	# Test template
	sections = config.get_sections()
	print(f'\n✓ Loaded {len(sections)} sections from template')

	# Show first few sections
	print('\nFirst 5 sections:')
	for section in sections[:5]:
		print(f'  - {section.name} ({section.type}): {section.word_count["min"]}-{section.word_count["max"]} words')

	# Test citation config
	citation_config = config.get_citation_config()
	print(f'\n✓ Citation style: {citation_config["style"]}')

	print('\n✅ All configurations loaded successfully!')


if __name__ == '__main__':
	test_config_loading()
