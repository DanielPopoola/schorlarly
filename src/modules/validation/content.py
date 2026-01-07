import json
from typing import Any
from src.models import (
    Section,
    IssueType,
    Severity,
    ValidationIssue,
)
from src.utils.logger import logger


class ContentValidator:
    def __init__(self, llm_client: Any, model: str):
        self.llm_client = llm_client
        self.model = model

    def validate(self, section: Section, questions: list[str]) -> list[ValidationIssue]:
        llm_issues: list[ValidationIssue] = []

        prompt_parts = [
            "You are an expert academic editor and stylistic reviewer.",
            "Your task is to evaluate a research paper section based on provided questions and style guidelines.",
            f"Section Title: {section.title}",
            f"Section Content:\n{section.content}",
            "Questions to be answered:\n" + "\n".join([f"- {q}" for q in questions]),
            """Style Guidelines:,
            - Tone: Professional, objective, and analytical academic prose.,
            - Clarity: Clear, concise sentences. Avoid unnecessary jargon or define it clearly.,
            - Flow: Logical transitions between paragraphs and arguments. The section should read cohesively.,
            - Terminology Consistency: Use consistent terminology throughout the section. Refer to key terms provided in the drafting context (if any) and ensure they are used appropriately.,
            Your output MUST be a JSON object with two main keys: 'question_coverage' and 'style_issues'.,
            ,
            ### QUESTION COVERAGE EVALUATION",
            For each question, determine if it has been 'FULLY_ADDRESSED', 'PARTIALLY_ADDRESSED', or 'NOT_ADDRESSED'. Provide a concise 'justification'.
            Example:,
            question_coverage: [\n  {\"question\": \"What are microplastics?\", \"addressed\": \"FULLY_ADDRESSED\",
              \"justification\": \"The section provides a clear definition and examples.\"},\n  
              {\"question\": \"Impact on ecosystems?\", \"addressed\": \"PARTIALLY_ADDRESSED\", \"justification\": \"Only marine impacts are discussed, not freshwater.\"}
]",
            ### STYLE ISSUES EVALUATION,
            Identify any issues related to the style guidelines. For each issue, provide 'issue_type' (e.g., 'STYLE_MISMATCH', 'TERMINOLOGY_INCONSISTENT', 'LACK_CLARITY', 'POOR_FLOW'), 'severity' (CRITICAL, WARNING, INFO), 'message', and a brief 'suggestion'.",
            Example:,
            "\"style_issues\": [\n  {\"issue_type\": \"STYLE_MISMATCH\", \"severity\": \"WARNING\", \"message\": \"Tone occasionally becomes informal.\", \"suggestion\": \"Maintain a consistently objective tone.\"},\n  
            {\"issue_type\": \"TERMINOLOGY_INCONSISTENT\", \"severity\": \"INFO\", \"message\": \"Used 'tiny plastic bits' instead of 'microplastics'.\", \"suggestion\": \"Ensure consistent use of defined key terms.\"}
]",
    
            Final JSON Output:""",
        ]

        prompt = "\n".join(prompt_parts)

        try:
            llm_response_text = self._call_llm(prompt, max_tokens=2000)
            llm_response_json = self._clean_json(llm_response_text)
            llm_evaluation = json.loads(llm_response_json)

            # Process question coverage
            question_coverage_results = llm_evaluation.get("question_coverage", [])
            missing_questions = []
            for qc_result in question_coverage_results:
                if qc_result.get("addressed") in [
                    "PARTIALLY_ADDRESSED",
                    "NOT_ADDRESSED",
                ]:
                    missing_questions.append(qc_result["question"])

            if missing_questions:
                llm_issues.append(
                    ValidationIssue(
                        issue_type=IssueType.QUESTION_NOT_ANSWERED,
                        severity=Severity.CRITICAL,  # Flag as critical if questions are missed
                        message=f"The following questions were not fully addressed: {'; '.join(missing_questions)}",
                        suggestion="Review the section and ensure all assigned questions are thoroughly answered.",
                        location="",
                    )
                )

            # Process style issues
            style_issues_data = llm_evaluation.get("style_issues", [])
            for si_data in style_issues_data:
                try:
                    llm_issues.append(
                        ValidationIssue(
                            issue_type=IssueType(
                                si_data.get("issue_type", "STYLE_MISMATCH")
                            ),
                            severity=Severity(si_data.get("severity", "WARNING")),
                            message=si_data.get("message", "Style issue detected."),
                            suggestion=si_data.get("suggestion"),
                            location="",
                        )
                    )
                except ValueError as e:
                    logger.warning(
                        f"LLM returned invalid enum for issue_type or severity: {e}. Data: {si_data}"
                    )
                    # Fallback to a generic issue if parsing fails
                    llm_issues.append(
                        ValidationIssue(
                            issue_type=IssueType.STYLE_MISMATCH,
                            severity=Severity.WARNING,
                            message=f"Generic style issue: {si_data.get('message', 'Unparseable LLM style issue.')}",
                            suggestion=si_data.get("suggestion"),
                            location="",
                        )
                    )

        except json.JSONDecodeError:
            llm_issues.append(
                ValidationIssue(
                    issue_type=IssueType.STYLE_MISMATCH,
                    severity=Severity.CRITICAL,
                    message="LLM failed to return a valid JSON response for content validation. Cannot assess style and question coverage.",
                    suggestion="Check LLM output and prompt for formatting issues.",
                    location="",
                )
            )
        except Exception as e:
            logger.error(f"Error during LLM content validation: {e}")
            llm_issues.append(
                ValidationIssue(
                    issue_type=IssueType.STYLE_MISMATCH,
                    severity=Severity.CRITICAL,
                    message="An unexpected error occurred during LLM content validation.",
                    suggestion="Review validation module and LLM client for issues.",
                    location="",
                )
            )

        return llm_issues

    def _call_llm(self, prompt: str, max_tokens: int) -> str:
        try:
            # Try Anthropic-style client
            response = self.llm_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except AttributeError:
            pass

        try:
            # Try OpenAI-style client
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except AttributeError:
            pass

        raise ValueError("LLM client not supported or failed to provide a response")

    def _clean_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
