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

    def get_text(self) -> str:
        if self.text is None:
            with open(self.path, "r") as f:
                self.text = f.read()
        return self.text

    @abstractmethod
    def prerun_checks(self) -> bool:
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

    @abstractmethod
    def get_line_replacements(self) -> List[ReplaceLineFixableIssue]:
        pass

    @abstractmethod
    def get_line_insertions(self) -> List[InsertLineIssue]:
        pass

    @abstractmethod
    def get_line_deletions(self) -> List[DeleteLineIssue]:
        pass

    def _process_line_replacements(self) -> None:
        line_lookup = self.get_line_number_lookup()
        replacements = self.get_line_replacements()
        deletions = self.get_line_deletions()
        for line_issue in deletions + replacements:
            new_line = line_issue.fix()
            lookedup_line = line_lookup[line_issue.line]
            logger.success(
                f"Replacing line {line_issue.line} with content: {lookedup_line}"
            )
            line_lookup[line_issue.line] = new_line

        self.text = "\n".join(line_lookup.values())

    def _process_line_insertions(self) -> None:
        sorted_insertions = sorted(self.get_line_insertions(), key=lambda x: x.line)
        logger.info(
            f"Found {len(sorted_insertions)} line insertions",
            insertions=sorted_insertions,
        )
        final_lines: List[str] = []

        for line_no, line_content in self.get_line_number_lookup().items():
            for insert in sorted_insertions:
                if insert.line == line_no:
                    final_lines.append(insert.insert_content)
                    break
            else:
                final_lines.append(line_content)
        self.text = "\n".join(final_lines)

    def _process_deletions(self) -> None:
        final_lines = []
        line_lookup = self.get_line_number_lookup()
        for line_no, line_content in line_lookup.items():
            if line_content == DELETE_LINE_MESSAGE:
                del line_lookup[line_no]
            else:
                final_lines.append(line_content)
        self.text = "\n".join(final_lines)

    def generate_v2(self) -> str:
        self._process_line_replacements()
        self._process_line_insertions()
        self._process_deletions()
        return self.get_text()
