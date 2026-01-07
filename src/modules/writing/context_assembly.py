from dataclasses import dataclass
from src.models import GlobalState, SectionSummary, Claim

from src.storage.claim import ClaimStore
from src.storage.embedding import EmbeddingProvider
import numpy as np
import faiss


@dataclass
class DraftingContext:
    thesis: str
    relevant_summaries: list[SectionSummary]
    previous_section_text: str | None
    relevant_claims: list[Claim]
    key_terms: dict[str, str]
    questions: list[str]
    section_id: int
    section_title: str


class ContextAssembler:
    def __init__(self, claim_store: ClaimStore, embedding_provider: EmbeddingProvider):
        self.claim_store = claim_store
        self.embedding_provider = embedding_provider

    def assemble(
        self,
        section_id: int,
        section_title: str,
        questions: list[str],
        global_state: GlobalState,
        previous_section_text: str | None = None,
    ) -> DraftingContext:
        # 1. Multi-query claim retrieval
        all_claims = []
        for q in questions:
            all_claims.extend(self.claim_store.search(q, top_k=5))

        seen_claim_ids = set()
        unique_claims = []
        for c in all_claims:
            if c.claim_id not in seen_claim_ids:
                unique_claims.append(c)
                seen_claim_ids.add(c.claim_id)

        # 2. Semantic search for relevant old sections
        relevant_summaries = self._find_relevant_summaries(
            section_title, questions, global_state.section_summaries
        )

        return DraftingContext(
            thesis=global_state.thesis,
            relevant_summaries=relevant_summaries,
            previous_section_text=previous_section_text,
            relevant_claims=unique_claims,
            key_terms=global_state.key_terms,
            questions=questions,
            section_id=section_id,
            section_title=section_title,
        )

    def _find_relevant_summaries(
        self, title: str, questions: list[str], summaries: list[SectionSummary]
    ) -> list[SectionSummary]:
        if not summaries:
            return []

        dimension = self.embedding_provider.dimension()
        index = faiss.IndexFlatIP(dimension)

        summary_texts = [f"{s.section_title} {s.summary}" for s in summaries]
        embeddings = [self.embedding_provider.encode(t) for t in summary_texts]

        vectors = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(vectors)
        index.add(vectors)  # type: ignore[arg-type]

        query_text = f"{title} {' '.join(questions)}"
        query_embedding = self.embedding_provider.encode(query_text)
        query_vector = np.array([query_embedding], dtype="float32")
        faiss.normalize_L2(query_vector)

        k = min(3, len(summaries))
        _, ids = index.search(query_vector, k)  # type: ignore[arg-type]

        relevant = []
        seen_ids = set()
        for i in ids[0]:
            if i != -1 and summaries[i].section_id not in seen_ids:
                relevant.append(summaries[i])
                seen_ids.add(summaries[i].section_id)

        return relevant
