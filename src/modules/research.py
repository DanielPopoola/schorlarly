from src.storage.claim import ClaimStore
from src.modules.search_provider import SearchProvider
from src.modules.claim_extractor import ClaimExtractor
from src.models import Claim
from src.utils.logger import logger


class ResearchModule:
    def __init__(
        self,
        search_provider: SearchProvider,
        claim_extractor: ClaimExtractor,
        claim_store: ClaimStore,
    ):
        self.search_provider = search_provider
        self.claim_extractor = claim_extractor
        self.claim_store = claim_store

    def execute(self, topic: str, max_papers: int = 10) -> dict[str, int]:
        logger.info(f"Starting research for topic: {topic}")

        stats = {
            "papers_found": 0,
            "papers_processed": 0,
            "papers_failed": 0,
            "claims_extracted": 0,
            "claims_stored": 0,
        }

        try:
            logger.info(f"Searching for papers about: {topic}")
            search_results = self.search_provider.search(topic, max_papers)
            stats["papers_found"] = len(search_results)

            logger.info(f"Found {len(search_results)} papers")

            for idx, result in enumerate(search_results, 1):
                logger.info(
                    f"Processing paper {idx}/{len(search_results)}: {result.title}"
                )

                try:
                    claims = self.claim_extractor.extract_from_search_result(result)
                    stats["claims_extracted"] += len(claims)

                    stored = self._store_claims(claims)
                    stats["claims_stored"] += stored
                    stats["papers_processed"] += 1

                    logger.info(
                        f"Extracted {len(claims)} claims from {result.source_id}"
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to process paper {result.source_id}: {e}",
                        exc_info=True,
                    )
                    stats["papers_failed"] += 1
                    continue

            logger.info(
                f"Research complete: "
                f"Processed {stats['papers_processed']}/{stats['papers_found']} papers, "
                f"extracted {stats['claims_extracted']} claims, "
                f"stored {stats['claims_stored']} claims"
            )

            if stats["papers_failed"] > 0:
                logger.warning(f"{stats['papers_failed']} papers failed to process")

            return stats

        except Exception as e:
            logger.error(f"Research phase failed: {e}", exc_info=True)
            raise

    def _store_claims(self, claims: list[Claim]) -> int:
        stored = 0

        for claim in claims:
            try:
                self.claim_store.add(claim)
                stored += 1
            except Exception as e:
                logger.warning(f"Failed to store claim {claim.claim_id}: {e}")
                continue

        return stored
