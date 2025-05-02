from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List

import diskcache
import instructor
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field, FilePath

cache = diskcache.Cache("./data/cache/editing")
patched_client = instructor.from_litellm(completion=completion)

DELETE_LINE_MESSAGE = ">>>>>>>>>>>>>>DELETE<<<<<<<<<<<<<<<"


class FixedLine(BaseModel):
    "The fix for a given line of content. It must include the entire line replaced, not just the partial fix."

    replacement_content: str = Field(description="The replacement content for the line")


@dataclass(frozen=True, order=True)
class LineIssue:
    line: int
    issue_message: List[str]


@dataclass(frozen=True, order=True)
class ReplaceLineFixableIssue(LineIssue):
    existing_content: str

    @cache.memoize()
    def fix(self) -> str:
        """
        Fix the line issue using Anthropic's API.

        Returns:
            The corrected line as a string, or the original line if fixing failed.
        """

        try:
            issues_str = "\n".join(self.issue_message)
            logger.info(f"Fixing line issue: {issues_str}")
            # Prepare prompt for Anthropic
            prompt = f"""Rewrite the following line:

<line number={self.line}>
{self.existing_content}
</line>

To fix the following issue:

<issue>
{self.issue_message}
</issue>

Only return the rewritten line. Do not include the line number or any other text.
"""

            # Call Anthropic API
            message = patched_client.chat.completions.create(
                model="anthropic/claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.25,  # Be precise
                messages=[{"role": "user", "content": prompt}],
                response_model=FixedLine,
            )

            return message.replacement_content
        except Exception as e:
            logger.error(f"Error fixing line issue: {e}")
            return self.existing_content


@dataclass(frozen=True, order=True)
class InsertLineIssue:
    line: int
    insert_content: str


@dataclass(frozen=True, order=True)
class DeleteLineIssue(ReplaceLineFixableIssue):
    def fix(self) -> str:
        return DELETE_LINE_MESSAGE


class BaseEditor(ABC, BaseModel):
    path: FilePath
    text: str | None = None
    replacements: List[ReplaceLineFixableIssue] = Field(
        default_factory=list, repr=False
    )
    insertions: List[InsertLineIssue] = Field(default_factory=list, repr=False)
    deletions: List[DeleteLineIssue] = Field(default_factory=list, repr=False)

    def get_text(self) -> str:
        if self.text is None:
            with open(self.path, "r") as f:
                self.text = f.read()
        return self.text

    @abstractmethod
    def prerun_checks(self) -> bool:
        pass

    # Add methods for subclasses to add issues
    def add_replacement(self, issue: ReplaceLineFixableIssue):
        self.replacements.append(issue)

    def add_insertion(self, issue: InsertLineIssue):
        self.insertions.append(issue)

    def add_deletion(self, issue: DeleteLineIssue):
        self.deletions.append(issue)

    @abstractmethod
    def collect_issues(self) -> None:
        """Subclasses must implement this method to populate the internal issue lists."""
        pass

    def get_line_number_lookup(self) -> Dict[int, str]:
        return {
            line_number: line_content
            for line_number, line_content in enumerate(self.get_text().split("\n"), 1)
        }

    def get_text_with_line_numbers(self) -> str:
        return "\n".join(
            sorted(
                [
                    f"{line_number}: {line_content}"
                    for line_number, line_content in self.get_line_number_lookup().items()
                ]
            )
        )

    def generate_v2(self) -> str:
        # Ensure text is loaded
        self.get_text()
        # Let subclass populate the issues
        self.collect_issues()

        initial_line_lookup = self.get_line_number_lookup()
        changes: Dict[int, str] = {}  # Store results of fixes/deletions

        # Process replacements
        for issue in self.replacements:
            new_content = issue.fix()
            changes[issue.line] = new_content
            logger.success(f"Replacing line {issue.line} with content: {new_content}")

        # Process deletions
        for issue in self.deletions:
            changes[issue.line] = DELETE_LINE_MESSAGE  # Mark for deletion
            logger.warning(f"Deleting line {issue.line}: {issue.existing_content}")

        final_lines: List[str] = []
        sorted_insertions = sorted(self.insertions, key=lambda x: x.line)
        insertion_idx = 0

        # Iterate through original lines, applying changes and insertions
        for line_no, original_content in sorted(initial_line_lookup.items()):
            # Process insertions BEFORE this line number
            while (
                insertion_idx < len(sorted_insertions)
                and sorted_insertions[insertion_idx].line == line_no
            ):
                insert_issue = sorted_insertions[insertion_idx]
                final_lines.append(insert_issue.insert_content)
                logger.info(
                    f"Inserting before line {line_no}: {insert_issue.insert_content}"
                )
                insertion_idx += 1

            # Process change/deletion for this line number
            if line_no in changes:
                change_content = changes[line_no]
                if change_content != DELETE_LINE_MESSAGE:
                    final_lines.append(change_content)
                # else: line is deleted, do nothing
            else:
                # No change, keep original content
                final_lines.append(original_content)

        # Handle any insertions that should occur after the last line
        while insertion_idx < len(sorted_insertions):
            insert_issue = sorted_insertions[insertion_idx]
            logger.info(
                f"Inserting after last line ({insert_issue.line}): {insert_issue.insert_content}"
            )
            final_lines.append(insert_issue.insert_content)
            insertion_idx += 1

        self.text = "\n".join(final_lines)
        return self.get_text()
