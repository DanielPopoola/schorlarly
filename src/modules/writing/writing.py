from typing import Any
from src.models import (
    GlobalState,
    Section,
    SectionSummary,
)
from src.storage.claim import ClaimStore
from src.storage.embedding import EmbeddingProvider
from src.utils.logger import logger
from .context_assembly import ContextAssembler
from .prompt_builder import build_drafting_prompt
from .drafting import DraftingEngine, SectionParser
from .ledger_update import LedgerUpdater


class WritingModule:
    def __init__(
        self,
        claim_store: ClaimStore,
        embedding_provider: EmbeddingProvider,
        llm_client: Any,
        model: str,
    ):
        self.context_assembler = ContextAssembler(claim_store, embedding_provider)
        self.drafting_engine = DraftingEngine(llm_client, model)
        self.section_parser = SectionParser()
        self.ledger_updater = LedgerUpdater(llm_client, model)

    def write_section(
        self,
        section_id: int,
        section_title: str,
        questions: list[str],
        global_state: GlobalState,
        previous_section_text: str | None = None,
    ) -> tuple[Section, SectionSummary]:
        logger.info(f"Writing Section {section_id}: {section_title}")

        context = self.context_assembler.assemble(
            section_id, section_title, questions, global_state, previous_section_text
        )

        prompt = build_drafting_prompt(context)

        raw_text = self.drafting_engine.draft(prompt)

        section = self.section_parser.parse(raw_text, section_id)
        section = section.__class__(
            section_id=section.section_id,
            title=section_title,
            content=section.content,
            citations=section.citations,
            word_count=section.word_count,
            status=section.status,
            created_at=section.created_at,
        )

        summary = self.ledger_updater.update(section, global_state)

        logger.info(
            f"Section {section_id} written. Words: {section.word_count}, Citations: {len(section.citations)}"
        )

        return section, summary
