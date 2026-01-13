from dataclasses import dataclass
from typing import Any


@dataclass
class SourceRelevance:
	source_id: str
	score: float
	matching_keywords: list[str]


class SourceFilter:
	def filter_by_relevance(
		self, sources: list[dict[str, Any]], objective: str, min_score: float = 0.15, top_k: int = 5
	) -> list[dict[str, Any]]:
		"""Filter global sources by relevance to section objective"""
		objective_keywords = self._extract_keywords(objective)

		scored_sources = []
		for source in sources:
			score = self._calculate_relevance(source, objective_keywords)
			if score >= min_score:
				scored_sources.append((source, score))

		# Sort by score, take top K
		scored_sources.sort(key=lambda x: x[1], reverse=True)

		# Fallback: if no sources pass min_score but we have sources, take top 2
		if not scored_sources and sources:
			all_scored = []
			for source in sources:
				all_scored.append((source, self._calculate_relevance(source, objective_keywords)))
			all_scored.sort(key=lambda x: x[1], reverse=True)
			return [s[0] for s in all_scored[:2]]

		return [s[0] for s in scored_sources[:top_k]]

	def _extract_keywords(self, text: str) -> set[str]:
		"""Extract meaningful keywords from text"""
		# Remove punctuation and lowercase
		import re

		text = re.sub(r'[^\w\s]', '', text.lower())
		words = text.split()

		# Filter: length >= 3, not very common words
		stop_words = {
			'which',
			'their',
			'about',
			'should',
			'these',
			'those',
			'there',
			'where',
			'would',
			'could',
			'point',
			'study',
			'paper',
			'section',
			'provide',
			'discuss',
			'present',
			'address',
		}
		keywords = {w for w in words if len(w) >= 3 and w not in stop_words}
		return keywords

	def _calculate_relevance(self, source: dict[str, Any], objective_keywords: set[str]) -> float:
		"""Calculate relevance score (0-1) based on keyword overlap"""
		abstract = source.get('abstract', '').lower()
		title = source.get('title', '').lower()

		abstract_keywords = self._extract_keywords(abstract)
		title_keywords = self._extract_keywords(title)

		# Weighted overlap: title matches worth more
		title_overlap = len(objective_keywords & title_keywords)
		abstract_overlap = len(objective_keywords & abstract_keywords)

		if not objective_keywords:
			return 0.0

		# Score: 60% title, 40% abstract
		score = (title_overlap * 0.6 + abstract_overlap * 0.4) / len(objective_keywords)
		return min(score, 1.0)
