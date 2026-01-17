from pathlib import Path
from src.core.context_manager import ContextManager
from src.research.searcher import Paper


def test_citation_registry():
	"""Test global citation numbering."""

	# Create fresh context manager
	context_manager = ContextManager()

	# Simulate Background section citing 3 papers
	paper1 = Paper(
		title='Machine Learning Basics',
		authors=['Smith, J.'],
		abstract='Introduction to ML',
		year=2020,
		url='https://example.com/1',
		source='test',
	)

	paper2 = Paper(
		title='Deep Learning Advanced',
		authors=['Doe, A.'],
		abstract='Advanced DL topics',
		year=2021,
		url='https://example.com/2',
		source='test',
	)

	paper3 = Paper(
		title='Neural Networks',
		authors=['Lee, C.'],
		abstract='NN fundamentals',
		year=2019,
		url='https://example.com/3',
		source='test',
	)

	# Register papers as if Background section did it
	num1 = context_manager.register_paper(paper1)
	num2 = context_manager.register_paper(paper2)
	num3 = context_manager.register_paper(paper3)

	print(f'Background section citations: [{num1}], [{num2}], [{num3}]')
	assert num1 == 1
	assert num2 == 2
	assert num3 == 3

	# Simulate Limitations section citing 2 NEW papers
	paper4 = Paper(
		title='System Limitations',
		authors=['Wang, K.'],
		abstract='Common limitations',
		year=2022,
		url='https://example.com/4',
		source='test',
	)

	paper5 = Paper(
		title='Future Work',
		authors=['Kumar, R.'],
		abstract='Research directions',
		year=2023,
		url='https://example.com/5',
		source='test',
	)

	num4 = context_manager.register_paper(paper4)
	num5 = context_manager.register_paper(paper5)

	print(f'Limitations section citations: [{num4}], [{num5}]')
	assert num4 == 4  # Continues from Background
	assert num5 == 5

	# Test duplicate detection - citing paper1 again
	num1_again = context_manager.register_paper(paper1)
	print(f'Re-citing paper1: [{num1_again}]')
	assert num1_again == 1  # Same number as before

	# Check registry state
	print(f'\nTotal unique papers: {len(context_manager.citation_registry)}')
	assert len(context_manager.citation_registry) == 5

	print('\nRegistry contents:')
	for key, (num, paper_dict) in sorted(context_manager.citation_registry.items(), key=lambda x: x[1][0]):
		print(f'  [{num}] {paper_dict["title"]} ({paper_dict["year"]})')

	print('\n✅ All tests passed!')


if __name__ == '__main__':
	test_citation_registry()
