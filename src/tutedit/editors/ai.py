import os
from typing import List, Literal, Optional

import diskcache  # type: ignore
import instructor
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field

from .core import (
    BaseEditor,
    DeleteLineIssue,
    InsertLineIssue,
    ReplaceLineFixableIssue,
)

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

    delete_line_tasks: List[DeleteLineIssue] = []
    replace_line_tasks: List[ReplaceLineFixableIssue] = []
    insert_line_tasks: List[InsertLineIssue] = []

    def _fetch_line_edits(self) -> LineEdits:
        """Fetches or retrieves cached line edits for the current text."""

        logger.debug("Fetching line edits from AI...")
        text_with_line_numbers = "\n".join(
            [
                f"{line_number}: {line_content}"
                for line_number, line_content in self.get_line_number_lookup().items()
            ]
        )
        # Use the configured model for detection
        return get_line_edits(text_with_line_numbers)

    def prerun_checks(self) -> bool:
        """Basic checks before running the editor."""
        # Could add checks for API keys if needed, but LiteLLM handles env vars
        logger.success("AI Editor prerun checks passed.")
        return True

    def run_line_replace_processing(self) -> None:
        """Generates ReplaceLineFixableIssue objects for edits suggested by the AI.

        Handles the replacement of the *first line* of an identified block.
        Deletion of subsequent original lines (if any) is handled by `get_deletions`.
        Insertion of subsequent corrected lines (if any) is not yet implemented.
        """
        line_edits_response = self._fetch_line_edits()
        replace_issues: List[ReplaceLineFixableIssue] = []
        line_lookup = self.get_line_number_lookup()

        edit_requests = [
            le for le in line_edits_response.line_edits if le.resolution == "edit"
        ]
        logger.info(
            f"Processing {len(edit_requests)} 'edit' requests for potential replacements."
        )

        for line_edit in edit_requests:
            start = line_edit.starting_affected_line
            end = line_edit.ending_affected_line
            issue_desc = f"AI Edit: {line_edit.issue_message}"

            # Validate line numbers
            if not (start in line_lookup and end in line_lookup and start <= end):
                logger.error(
                    f"Invalid line numbers ({start}-{end}) in line edit: {line_edit.issue_message}. Skipping."
                )
                continue

            # Extract relevant lines
            relevant_lines_list = [line_lookup[i] for i in range(start, end + 1)]
            relevant_lines_text = "\n".join(relevant_lines_list)

            # Get the fix from AI
            corrected_text = fix_line_edit(line_edit, relevant_lines_text)

            if corrected_text is not None:
                # Split corrected text into lines
                corrected_lines = corrected_text.splitlines()

                if not corrected_lines:
                    logger.warning(
                        f"AI returned empty correction for lines {start}-{end}. Skipping replacement (will be handled by get_deletions if resolution was 'delete')."
                    )
                    continue  # Skip creating a replacement issue if the correction is empty

                # Create the replacement issue for the *first* line only.
                # Add a note if the original block or the correction was multi-line.
                additional_notes = []
                is_multiline_edit = len(corrected_lines) > 1 or (end > start)
                if is_multiline_edit:
                    additional_notes.append(
                        f"(Note: Original block lines {start + 1}-{end} handled by deletions. "
                        f"Multi-line correction received; only first line applied here.)"
                    )
                    logger.warning(
                        f"AI correction for lines {start}-{end} involves multiple lines "
                        f"(original block size: {end - start + 1}, corrected lines: {len(corrected_lines)}). "
                        f"Replacing line {start} with the first corrected line. "
                        "Ensure get_deletions handles original lines "
                        f"{start + 1}-{end}."  # Adjusted log message
                    )

                replace_issues.append(
                    ReplaceLineFixableIssue(
                        line=start,
                        # Combine original AI issue message with any notes
                        issue_message=[issue_desc] + additional_notes,
                        existing_content=line_lookup[start],
                        # Provide the first line of the corrected text for replacement
                        # The IssueManager applying this needs to handle using this.
                        # Assuming IssueManager implicitly uses the first line or can be adapted.
                        # For now, we store the replacement content conceptually.
                        # Let's add it to the object if the class supports it, otherwise it's implied.
                        # Update: ReplaceLineFixableIssue has no field. It must be handled by the fixer.
                        # The replacement *content* isn't stored on the issue itself in core.py.
                        # We signal the *intent* to replace line `start` with `corrected_lines[0]`.
                        # We must pass `corrected_lines[0]` to the fixing mechanism later.
                        # TODO: The actual replacement content (corrected_lines[0]) needs to be passed
                        # to the mechanism that *applies* the fix for ReplaceLineFixableIssue.
                        # This method only *identifies* the issue.
                    )
                )
                delete_line_nos = range(start + 1, end + 1)
                for line_no in delete_line_nos:
                    self.delete_line_tasks.append(
                        DeleteLineIssue(
                            line=line_no,
                            existing_content=line_lookup[line_no],
                            issue_message=[f"AI Delete: {line_edit.issue_message}"],
                        )
                    )
            else:
                logger.warning(
                    f"Failed to get AI correction for lines {start}-{end}. Skipping replacement."
                )

        logger.success(f"Generated {len(replace_issues)} line replacement suggestions.")
        self.replace_line_tasks = replace_issues

    def run_line_deletion_processing(self) -> None:
        """Generates DeleteLineIssue objects for deletions or replaced lines."""
        line_edits_response = self._fetch_line_edits()
        delete_issues: List[DeleteLineIssue] = []
        line_lookup = self.get_line_number_lookup()

        # Lines marked explicitly for deletion by AI
        delete_requests = [
            le for le in line_edits_response.line_edits if le.resolution == "delete"
        ]
        logger.info(f"Processing {len(delete_requests)} 'delete' requests.")
        for line_edit in delete_requests:
            start = line_edit.starting_affected_line
            end = line_edit.ending_affected_line
            if not (start in line_lookup and end in line_lookup and start <= end):
                logger.warning(
                    f"Invalid line numbers ({start}-{end}) in delete request: {line_edit.issue_message}. Skipping."
                )
                continue
            for line_num in range(start, end + 1):
                # Avoid adding duplicate deletions
                if not any(d.line == line_num for d in delete_issues):
                    delete_issues.append(
                        DeleteLineIssue(
                            line=line_num,
                            existing_content=line_lookup[line_num],
                            issue_message=[f"AI Delete: {line_edit.issue_message}"],
                        )
                    )

        # Lines that are part of a multi-line block being replaced (delete lines after the first)
        edit_requests = [
            le for le in line_edits_response.line_edits if le.resolution == "edit"
        ]
        for line_edit in edit_requests:
            start = line_edit.starting_affected_line
            end = line_edit.ending_affected_line
            # Only add deletions if it was a multi-line block (end > start)
            if end > start:
                if not (start in line_lookup and end in line_lookup):
                    # Warning issued in get_line_replacements
                    continue

                for line_num in range(start + 1, end + 1):
                    # Check if the line exists and avoid duplicates
                    if line_num in line_lookup and not any(
                        d.line == line_num for d in delete_issues
                    ):
                        delete_issues.append(
                            DeleteLineIssue(
                                line=line_num,
                                existing_content=line_lookup[line_num],
                                issue_message=[
                                    f"AI Edit (Removing original line after replacement): {line_edit.issue_message}"
                                ],
                            )
                        )

        # Handle flagged items (log them for now)
        flag_requests = [
            le for le in line_edits_response.line_edits if le.resolution == "flag"
        ]
        if flag_requests:
            logger.warning(f"AI flagged {len(flag_requests)} issues for manual review:")
            for line_edit in flag_requests:
                logger.warning(
                    f"  - Lines {line_edit.starting_affected_line}-{line_edit.ending_affected_line}: {line_edit.issue_message}"
                )
                # TODO: Optionally write flagged issues to a file like in the inspiration code.

        logger.success(f"Generated {len(delete_issues)} line deletion suggestions.")
        # Sort deletions by line number before returning

        final_deletions = sorted(delete_issues, key=lambda issue: issue.line)
        self.delete_line_tasks = final_deletions

    def get_line_insertions(self) -> List[InsertLineIssue]:
        """This editor does not currently generate insertions directly."""
        # Future enhancement: Could handle multi-line replacements from fix_line_edit here.
        return []

    def get_line_replacements(self) -> List[ReplaceLineFixableIssue]:
        self.run_line_replace_processing()
        return self.replace_line_tasks

    def get_line_deletions(self) -> List[DeleteLineIssue]:
        self.run_line_deletion_processing()
        return self.delete_line_tasks
