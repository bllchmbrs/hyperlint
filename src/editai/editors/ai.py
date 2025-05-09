import os
from typing import List, Literal, Optional

import diskcache  # type: ignore
import instructor
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field

from .core import BaseEditor, DeleteLineIssue, InsertLineIssue

# Constants
# Use a separate cache directory for this editor
cache = diskcache.Cache("./data/cache/ai_editor")
patched_client = instructor.from_litellm(completion=completion)

MODEL_NAME = os.getenv("AI_EDITOR_MODEL", "openai/o3-mini-2025-01-31")


class LineEdit(BaseModel):
    """Represents a single identified issue and proposed resolution for a range of lines."""

    starting_affected_line: int = Field(
        description="The 1-indexed starting line number of the text block with the issue."
    )
    ending_affected_line: int = Field(
        description="The 1-indexed ending line number of the text block with the issue."
    )
    issue_message: str = Field(
        description="A concise description of the identified issue (e.g., 'Inconsistent formatting', 'Redundant explanation', 'Awkward phrasing')."
    )
    resolution: Literal["edit", "delete", "flag"] = Field(
        description=(
            "The suggested resolution: 'edit' to modify the text, "
            "'delete' to remove the text block, "
            "'flag' to report the issue without automated changes (e.g., for complex errors or code blocks)."
        )
    )


class LineEdits(BaseModel):
    """A collection of line edits identified in the text."""

    line_edits: List[LineEdit] = Field(
        description="A list of identified issues and their proposed resolutions."
    )


class CorrectedText(BaseModel):
    """Represents the corrected text block."""

    corrected_text: str = Field(
        description="The corrected version of the text block provided."
    )


def get_line_edits(text_with_line_numbers: str) -> LineEdits:
    """Identifies potential issues in the text using an AI model.

    Args:
        text_with_line_numbers: The input text, with each line prefixed by its number.

    Returns:
        A LineEdits object containing the identified issues.
    """
    prompt = f"""You are an expert technical editor reviewing a document.

    Your task is to identify sections of the text that could be improved for clarity, conciseness, consistency, or formatting. Focus on improving the flow and readability for a technical audience.

    Here is the text with line numbers:
    <text>
    {text_with_line_numbers}
    </text>

    Identify issues and suggest a resolution for each:
    - 'edit': If the text can be clearly improved (e.g., fixing typos, rephrasing awkward sentences, correcting minor formatting). Provide a concise 'issue_message'.
    - 'delete': If a block of text (one or more lines) is redundant, unnecessary, or clearly erroneous and should be removed.
    - 'flag': If there's a significant issue you can identify but cannot confidently fix (e.g., missing information, a potentially incorrect technical statement, complex formatting problems, issues within code blocks). Use 'flag' for anything inside ``` blocks.

    Provide the starting and ending line number for each identified issue.
    Ensure the line ranges are accurate and cover the entire relevant text block for the issue.

    Return a list of identified issues and their resolutions.
    """
    try:
        logger.info(f"Requesting line edits using model: {MODEL_NAME}")
        response: LineEdits = patched_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_model=LineEdits,
            max_tokens=2048,  # Allow for potentially many edits
        )
        logger.success(
            f"Received {len(response.line_edits)} potential line edits from AI."
        )
        return response
    except Exception as e:
        logger.error(f"Error getting line edits from AI: {e}", exc_info=True)
        # Return empty list on error
        return LineEdits(line_edits=[])


def fix_line_edit(line_edit: LineEdit, relevant_lines: str) -> Optional[str]:
    """Generates corrected text for a given line edit using an AI model.

    Args:
        line_edit: The LineEdit object describing the issue.
        relevant_lines: The specific lines of text affected by the edit.

    Returns:
        The corrected text block as a single string, or None if correction fails.
    """
    prompt = f"""You are an expert technical editor tasked with fixing an issue in a specific text block.

    The identified issue is:
    <issue_message>
    {line_edit.issue_message}
    </issue_message>

    Here is the original text block (from line {line_edit.starting_affected_line} to {line_edit.ending_affected_line}):
    <original_text>
    {relevant_lines}
    </original_text>

    Your goal is to rewrite the original text block to resolve *only* the specified issue.
    - Maintain the original meaning and intent unless the issue is about factual correctness.
    - Preserve the original line breaks and indentation as much as possible, unless the issue is specifically about formatting.
    - Ensure the corrected text seamlessly fits back into the surrounding document.
    - ONLY return the corrected text block itself, without any extra explanations or formatting.

    Return the corrected text block.
    """
    try:
        logger.info(
            f"Requesting fix for lines {line_edit.starting_affected_line}-{line_edit.ending_affected_line} using model: {MODEL_NAME}"
        )
        # Using CorrectedText response model for structure, although the prompt asks for raw text.
        # This adds a layer of validation.
        response: CorrectedText = patched_client.chat.completions.create(
            model="anthropic/claude-3-haiku-20240307",
            messages=[{"role": "user", "content": prompt}],
            response_model=CorrectedText,
            max_tokens=1024,  # Should be enough for typical block edits
        )
        logger.success(
            f"Received corrected text for lines {line_edit.starting_affected_line}-{line_edit.ending_affected_line}."
        )
        return (
            response.corrected_text.strip()
        )  # Strip potential leading/trailing whitespace
    except Exception as e:
        logger.error(
            f"Error fixing line edit for lines {line_edit.starting_affected_line}-{line_edit.ending_affected_line}: {e}",
            exc_info=True,
        )
        return None  # Return None on error


# TODO: Implement AIEditor class inheriting from BaseEditor
class AIEditor(BaseEditor):
    """
    Editor that uses AI to identify and fix issues related to
    clarity, conciseness, consistency, and formatting in text.
    It can suggest edits, deletions, or flag issues for manual review.
    """

    def _fetch_line_edits(self) -> LineEdits:
        """Fetches or retrieves cached line edits for the current text."""

        logger.debug("Fetching line edits from AI...")
        text_with_line_numbers = self.get_text_with_line_numbers()  # Use helper
        # Use the configured model for detection
        return get_line_edits(text_with_line_numbers)

    def prerun_checks(self) -> bool:
        """Basic checks before running the editor."""
        # Could add checks for API keys if needed, but LiteLLM handles env vars
        logger.success("AI Editor prerun checks passed.")
        return True

    def collect_issues(self) -> None:
        """Collects issues identified by AI and translates them into insertions/deletions."""
        line_edits_response = self._fetch_line_edits()
        line_lookup = self.get_line_number_lookup()
        processed_lines = set()  # Track lines involved in an operation
        insertions_count = 0
        deletions_count = 0
        flagged_count = 0

        # Sort edits by starting line to process potentially overlapping edits predictably
        sorted_edits = sorted(
            line_edits_response.line_edits, key=lambda le: le.starting_affected_line
        )

        for line_edit in sorted_edits:
            start = line_edit.starting_affected_line
            end = line_edit.ending_affected_line
            resolution = line_edit.resolution
            issue_desc = f"AI {resolution.capitalize()}: {line_edit.issue_message}"

            # Validate line numbers against the original lookup
            if not (start in line_lookup and end in line_lookup and start <= end):
                logger.error(
                    f"Invalid line numbers ({start}-{end}) in line edit: {line_edit.issue_message}. Skipping."
                )
                continue

            # Check for overlap with already processed lines
            current_range = set(range(start, end + 1))
            if not current_range.isdisjoint(processed_lines):
                logger.warning(
                    f"Skipping line edit for lines {start}-{end} due to overlap with a previous edit: {line_edit.issue_message}"
                )
                continue

            # Mark lines as processed
            processed_lines.update(current_range)

            if resolution == "edit":
                # Extract relevant lines
                relevant_lines_list = [line_lookup[i] for i in range(start, end + 1)]
                relevant_lines_text = "\n".join(relevant_lines_list)

                # Get the fix from AI
                corrected_text = fix_line_edit(line_edit, relevant_lines_text)

                if corrected_text is not None:
                    if corrected_text.strip():  # Non-empty correction
                        corrected_lines = corrected_text.splitlines()

                        # 1. Add insertions for the corrected lines (inserted before original start)
                        for i, line_content in enumerate(corrected_lines):
                            # Insert each new line before the original start line.
                            # The BaseEditor process logic handles sequential insertions.
                            self.add_insertion(
                                InsertLineIssue(line=start, insert_content=line_content)
                            )
                            insertions_count += 1
                        logger.info(
                            f"Added {len(corrected_lines)} insertions for AI edit at lines {start}-{end}"
                        )

                        # 2. Add deletions for the original lines
                        for line_num in range(start, end + 1):
                            self.add_deletion(
                                DeleteLineIssue(
                                    line=line_num,
                                    existing_content=line_lookup[line_num],
                                    issue_message=[
                                        f"AI Edit (Deleting original line): {line_edit.issue_message}"
                                    ],
                                )
                            )
                            deletions_count += 1
                        logger.info(
                            f"Added {end - start + 1} deletions for AI edit at lines {start}-{end}"
                        )

                    else:  # Empty correction -> Treat as delete
                        logger.warning(
                            f"AI returned empty correction for lines {start}-{end}. Treating as 'delete'."
                        )
                        resolution = "delete"  # Fall through to delete logic
                else:  # Failed to get correction -> Treat as flag
                    logger.error(
                        f"Failed to get AI correction for lines {start}-{end}. Treating as 'flag'."
                    )
                    resolution = "flag"  # Fall through to flag logic

            if resolution == "delete":
                for line_num in range(start, end + 1):
                    self.add_deletion(
                        DeleteLineIssue(
                            line=line_num,
                            existing_content=line_lookup[line_num],
                            issue_message=[issue_desc],
                        )
                    )
                    deletions_count += 1
                logger.info(
                    f"Added {end - start + 1} deletions for AI delete at lines {start}-{end}"
                )

            if resolution == "flag":
                logger.warning(
                    f"Flagged by AI: Lines {start}-{end}: {line_edit.issue_message}"
                )
                flagged_count += 1
                # Optionally add to a separate list or file if needed

        logger.success(
            f"AI Editor finished collecting issues: {insertions_count} insertions, {deletions_count} deletions, {flagged_count} flagged."
        )
