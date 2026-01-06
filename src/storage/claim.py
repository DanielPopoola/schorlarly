import json
import numpy as np
import faiss
from pathlib import Path
from dataclasses import asdict
from dacite import from_dict

from .embedding import EmbeddingProvider
from src.models import Claim
from .helpers import EnumEncoder


class ClaimStore:
    def __init__(self, storage_path: Path, embedding_provider: EmbeddingProvider):
        self.storage_path = storage_path
        self.claims_file = storage_path / "claims.json"
        self.index_file = storage_path / "claims.faiss"
        self._claims_cache: dict[str, Claim] | None = None

        self.embedding_provider = embedding_provider
        self.storage_path.mkdir(parents=True, exist_ok=True)

        dimension = embedding_provider.dimension()
        self.index: faiss.IndexIDMap = self._load_or_create_index(dimension)

    def add(self, claim: Claim) -> None:
        claims = self._load_claims()
        if claim.claim_id in claims:
            return

        text = f"{claim.statement} {claim.context or ''}"
        embedding = self.embedding_provider.encode(text)

        self._validate_embedding(embedding)

        vector = np.array([embedding], dtype="float32")
        faiss.normalize_L2(vector)

        claim_id_int = self._claim_id_to_int(claim.claim_id)

        self.index.add_with_ids(vector, np.array([claim_id_int], dtype="int64"))  # type: ignore[arg-type]
        self._save_claim_to_json(claim)
        self._save_index()

    def get(self, claim_id: str) -> Claim | None:
        return self._load_claims().get(claim_id)

    def search(self, query: str, top_k: int = 5) -> list[Claim]:
        if self.index.ntotal == 0:
            return []

        embedding = self.embedding_provider.encode(query)
        self._validate_embedding(embedding)

        vector = np.array([embedding], dtype="float32")
        faiss.normalize_L2(vector)

        _, ids = self.index.search(vector, top_k)  # type: ignore[arg-type]

        claims = self._load_claims()
        results: list[Claim] = []

        for claim_id_int in ids[0]:
            if claim_id_int == -1:
                continue

            claim_id = self._int_to_claim_id(int(claim_id_int))
            claim = claims.get(claim_id)

            if claim:
                results.append(claim)

        return results

    def _load_or_create_index(self, dimension: int) -> faiss.IndexIDMap:
        if self.index_file.exists():
            index = faiss.read_index(str(self.index_file))
            if not isinstance(index, faiss.IndexIDMap):
                raise TypeError(f"Expected IndexIDMap, got {type(index)}")
            if index.d != dimension:
                raise ValueError("Embedding dimension mismatch with stored FAISS index")
            return index

        base_index = faiss.IndexFlatIP(dimension)  # cosine via normalization
        return faiss.IndexIDMap(base_index)

    def _save_index(self) -> None:
        faiss.write_index(self.index, str(self.index_file))

    def _load_claims(self) -> dict[str, Claim]:
        if self._claims_cache is not None:
            return self._claims_cache

        if not self.claims_file.exists():
            self._claims_cache = {}
            return {}

        with open(self.claims_file, "r") as f:
            data = json.load(f)
            self._claims_cache = {
                cid: from_dict(data_class=Claim, data=c_dict)
                for cid, c_dict in data.items()
            }

        return self._claims_cache

    def _save_claim_to_json(self, claim: Claim) -> None:
        claims = self._load_claims()
        claims[claim.claim_id] = claim

        output = {cid: asdict(c) for cid, c in claims.items()}
        with open(self.claims_file, "w") as f:
            json.dump(output, f, cls=EnumEncoder, indent=2)

    def _validate_embedding(self, embedding: list[float]) -> None:
        if len(embedding) != self.index.d:
            raise ValueError(
                f"Embedding dimension {len(embedding)} does not match index dimension {self.index.d}"
            )

    def _claim_id_to_int(self, claim_id: str) -> int:
        return abs(hash(claim_id)) % (2**63)

    def _int_to_claim_id(self, claim_id_int: int) -> str:
        claims = self._load_claims()
        for cid in claims.keys():
            if self._claim_id_to_int(cid) == claim_id_int:
                return cid
        raise KeyError("Claim ID not found for FAISS result")
