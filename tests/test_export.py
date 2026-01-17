"""
Test the Word exporter independently with mock data
"""

from pathlib import Path

from src.core.context_manager import ContextManager, SectionContext
from src.export.word_exporter import WordExporter


def create_mock_sections() -> list[SectionContext]:
	"""Create realistic test sections with different markdown features"""
	return [
		SectionContext(
			name='Introduction',
			content="""This paper presents an **AI-Powered Course Registration System** designed to streamline
the university course selection process. The system uses *machine learning* to provide personalized recommendations
and `automated conflict detection`.

The current manual registration process is time-consuming and error-prone. Students spend hours browsing catalogs
and checking prerequisites, often discovering conflicts after registration deadlines.""",
			key_points=[
				'AI-powered recommendation system',
				'Addresses time-consuming manual process',
				'Automated conflict detection',
			],
			citations=['[1]', '[2]'],
			word_count=87,
		),
		SectionContext(
			name='Background to the Study',
			content="""Course registration systems have evolved significantly over the past decade [1]. Traditional
systems require manual intervention for:

- Schedule conflict resolution
- Prerequisite checking
- Workload balancing
- Course availability tracking

Recent advances in **collaborative filtering** and **constraint satisfaction algorithms** have enabled more
intelligent systems [2]. Studies show that students using recommendation systems save an average of *2.5 hours*
per semester [3].

The implementation typically involves three key components:

1. Data collection and preprocessing
2. Machine learning model training
3. Real-time recommendation generation

Research by Smith et al. (2022) demonstrated that hybrid approaches combining rule-based and ML-based methods
achieve 78% recommendation accuracy [4].""",
			key_points=[
				'Traditional systems require manual conflict resolution',
				'Collaborative filtering enables intelligent recommendations',
				'Hybrid approaches achieve 78% accuracy',
			],
			citations=['[1]', '[2]', '[3]', '[4]'],
			word_count=142,
		),
		SectionContext(
			name='System Design',
			content="""The system architecture follows a **microservices pattern** with three main components:

**Backend API (Flask + Python)**
- RESTful endpoints for client interactions
- JWT-based authentication
- Business logic layer

**Recommendation Engine**
- SVD matrix factorization using `scikit-learn`
- Constraint satisfaction solver
- Periodic model retraining

**Frontend (React + TypeScript)**
- Interactive schedule builder
- Real-time availability updates
- Feedback collection interface

The database layer uses *PostgreSQL* for relational data and *Redis* for caching. This design achieves
sub-second response times for 95% of requests.""",
			key_points=[
				'Microservices architecture with three components',
				'SVD matrix factorization for recommendations',
				'PostgreSQL and Redis for data storage',
				'Sub-second response times',
			],
			citations=[],
			word_count=98,
		),
		SectionContext(
			name='System Implementation',
			content="""The recommendation engine was implemented using Python 3.11 and scikit-learn. The core
algorithm uses **Singular Value Decomposition (SVD)** to factorize the student-course enrollment matrix.

```python
from sklearn.decomposition import TruncatedSVD

# Factorize enrollment matrix
svd = TruncatedSVD(n_components=50)
user_factors = svd.fit_transform(enrollment_matrix)
course_factors = svd.components_

# Compute recommendations
scores = user_factors @ course_factors
```

The constraint satisfaction solver uses *backtracking with forward checking* to ensure all generated schedules
are valid. Key optimizations include:

- Redis caching for frequently accessed course data
- Asynchronous task processing with Celery
- Database query optimization using eager loading

Performance testing showed the system handles **500 concurrent users** with average response time of 340ms.""",
			key_points=[
				'SVD for matrix factorization',
				'Backtracking algorithm for constraint satisfaction',
				'Redis caching reduces database load',
				'Handles 500 concurrent users',
			],
			citations=[],
			word_count=126,
		),
		SectionContext(
			name='Test Results',
			content="""Comprehensive testing validated system functionality and performance.

**Unit Testing:**
- Backend: 67/67 tests passed (95% coverage)
- Frontend: 45/45 component tests passed
- Recommendation engine: 23/23 algorithm tests passed

**Performance Metrics:**
- Load test: 500 concurrent users supported
- Average response time: 340ms
- 95th percentile: 580ms
- Cache hit rate: 73%

**User Acceptance Testing:**
A pilot study with 50 students showed:
- 87% found recommendations relevant
- Average time saved: 2.1 hours per student
- 92% preferred AI system over manual selection

The recommendation accuracy (Precision@5) reached **0.78**, meaning 78% of top-5 recommendations were courses
students actually enrolled in [5].""",
			key_points=[
				'100% test pass rate across all modules',
				'340ms average response time',
				'87% user satisfaction rate',
				'0.78 recommendation precision',
			],
			citations=['[5]'],
			word_count=132,
		),
		SectionContext(
			name='Conclusion',
			content="""This project successfully developed an **AI-powered course registration system** that
addresses key challenges in university course selection. The system combines *collaborative filtering* with
*constraint satisfaction* to provide personalized, conflict-free schedule recommendations.

Key achievements include:

1. 78% recommendation accuracy (Precision@5)
2. 340ms average response time
3. 87% user satisfaction rate
4. 2.1 hours saved per student

The hybrid approach proved effective in balancing personalization with hard constraints. Future work could
explore deep learning models and expand to multi-semester planning.""",
			key_points=[
				'Successfully addresses course selection challenges',
				'Hybrid approach balances personalization and constraints',
				'Significant time savings and user satisfaction',
			],
			citations=[],
			word_count=92,
		),
	]


def test_word_export():
	"""Test Word document export with realistic content"""
	print('\n' + '=' * 60)
	print('Testing Word Exporter')
	print('=' * 60 + '\n')

	# Create mock context manager with test data
	context_file = Path('output/state/academic_transcript_context.json')
	context_manager = ContextManager(context_file)

	# Add mock sections
	# mock_sections = create_mock_sections()
	# print(f'Creating document with {len(mock_sections)} sections...\n')

	# for section in mock_sections:
	# context_manager.add_section(section)
	# print(f'✓ Added: {section.name} ({section.word_count} words, {len(section.citations)} citations)')

	# Create exporter config
	config = {
		'final_dir': 'output/final',
		'citation': {'style': 'IEEE'},
	}

	# Create exporter and export
	exporter = WordExporter(context_manager, config)

	print('\nExporting to Word...')
	output_path = exporter.export(
		project_name='test_export', project_title='BlockChain Secured Academic Transcript', author='Test Student'
	)

	# Verify output
	print(f'\n{"─" * 60}')
	print('EXPORT RESULTS')
	print(f'{"─" * 60}')
	print(f'Output file: {output_path}')
	print(f'File exists: {output_path.exists()}')
	print(f'File size: {output_path.stat().st_size / 1024:.2f} KB')

	# Show summary
	summary = context_manager.get_summary()
	print(f'\n{"─" * 60}')
	print('DOCUMENT SUMMARY')
	print(f'{"─" * 60}')
	print(f'Total sections: {summary["total_sections"]}')
	print(f'Total words: {summary["total_words"]:,}')
	print(f'Total citations: {summary["total_citations"]}')

	print(f'\n{"─" * 60}')
	print('WHAT TO CHECK IN THE WORD DOCUMENT:')
	print(f'{"─" * 60}')
	print('1. Title page with project title, author, and date')
	print('2. Section headings (should be Heading 1 style)')
	print('3. Bold text (check **bold** converted correctly)')
	print('4. Italic text (check *italic* converted correctly)')
	print('5. Code blocks (check `code` and ```python blocks)')
	print('6. Bullet lists (should be properly formatted)')
	print('7. Numbered lists (should be properly formatted)')
	print('8. References section at the end')
	print('9. Times New Roman 12pt font')
	print('10. 1.5 line spacing')

	print(f'\n✓ Test complete! Open the file: {output_path.absolute()}')

	return output_path


if __name__ == '__main__':
	import sys

	test_word_export()

	print('\n' + '=' * 60)
	print('All tests complete!')
	print('=' * 60)
