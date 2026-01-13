from typing import Any

from utils.llm_client import UnifiedLLMClient
from utils.logger import logger


class EditorAgent:
	def __init__(self, llm_client: UnifiedLLMClient):
		self.llm_client = llm_client

	def remove_redundancy(self, all_sections_content: list[str]) -> list[str]:
		logger.info('Running global coherence editor to remove redundancy...')

		# Combine all sections into a single string for LLM processing
		combined_content = '\n\n---\n\n'.join(all_sections_content)

		prompt = f"""
        You are an expert academic editor. Your task is to review a full research paper
        and identify significant redundancies, circular explanations, and duplicated content across its sections.
        
        The paper is provided below, with sections separated by '---'.
        
        # PAPER CONTENT
        {combined_content}
        
        # TASK
        Identify specific instances of:
        1. Repeated definitions or background information.
        2. Duplicate problem statements or objectives.
        3. Circular explanations where a concept is defined by itself or by something that also defines it.
        
        For each identified redundancy:
        - State the redundant content.
        - Indicate the primary section where it should be kept.
        - Propose a concise edit (or removal) for the other sections where it appears.
        
        Aim to make the paper more concise and logically flowing, ensuring each piece of information
        is presented optimally once.
        
        # OUTPUT FORMAT
        Provide a structured list of edits. If no significant redundancy is found, state that.
        Example:
        - Redundant content: "Neural networks are a series of algorithms..."
          - Keep in: Introduction
          - Edit in: Background (Remove or replace with "As defined in the Introduction...")
        - Redundant content: "The main objective is to reduce latency..."
          - Keep in: Objective of the Study
          - Edit in: Introduction (Rephrase to "This paper addresses the problem of reducing latency...")
        """

		try:
			self.llm_client.generate(prompt, max_tokens=3000)
			logger.info('Editor Agent output received.')
			# For now, we'll just return the original content.
			# A full implementation would parse the LLM's edit plan and apply it.
			# This is a placeholder for future, more complex parsing and application logic.
			return all_sections_content
		except Exception as e:
			logger.error(f'Editor Agent failed: {e}')
			return all_sections_content

	def _load_section_content(self, section_id: int, sections_dir: Any) -> str:
		# This method is a placeholder and assumes orchestrator will handle loading
		# For now, it just returns a mock content or an empty string
		return f'Content for section {section_id}'
