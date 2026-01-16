from src.core.config_loader import get_config
from src.llm.client import create_llm_client_from_config
from src.research.searcher import Paper
from src.research.validator import CitationValidator


def test_batch_validation():
	"""Test batch validation vs individual validation"""

	config = get_config()
	llm_client = create_llm_client_from_config(config.get_llm_config())
	validator = CitationValidator(llm_client, config.get_citation_config())

	# Create test papers
	papers = [
		Paper(
			title='Machine Learning for Course Recommendation Systems',
			authors=['Smith, J.', 'Doe, A.'],
			abstract='This paper presents a collaborative filtering approach for recommending courses to university students based on historical enrollment data.',
			year=2022,
			url='https://arxiv.org/example1',
			source='test',
		),
		Paper(
			title='Deep Learning in Medical Imaging',
			authors=['Johnson, B.'],
			abstract='We apply convolutional neural networks to detect anomalies in MRI scans with 95% accuracy.',
			year=2023,
			url='https://arxiv.org/example2',
			source='test',
		),
		Paper(
			title='Course Registration Optimization Using Constraint Satisfaction',
			authors=['Lee, C.'],
			abstract='We model course scheduling as a constraint satisfaction problem and solve it using backtracking algorithms.',
			year=2021,
			url='https://arxiv.org/example3',
			source='test',
		),
	]

	domain_keywords = ['machine learning', 'course registration', 'recommendation systems']

	# Test batch validation
	print('Testing batch validation...')
	start_tokens = llm_client.get_usage_stats()['total_tokens']

	results = validator.validate_batch(papers, domain_keywords)

	end_tokens = llm_client.get_usage_stats()['total_tokens']
	tokens_used = end_tokens - start_tokens

	print(f'\nTokens used: {tokens_used}')
	print(f'Papers validated: {len(results)}')
	print('\nResults:')
	for paper in papers:
		key = paper.url or paper.title
		result = results[key]
		print(f'  {paper.title[:50]}...')
		print(f'    Score: {result.relevance_score:.2f}')
		print(f'    Status: {result.status}')
		print()


if __name__ == '__main__':
	test_batch_validation()
