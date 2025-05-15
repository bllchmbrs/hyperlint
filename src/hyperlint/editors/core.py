import difflib
import json
from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import diskcache
import instructor
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field, FilePath
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

cache = diskcache.Cache("./data/cache/editing")
patched_client = instructor.from_litellm(completion=completion)

DELETE_LINE_MESSAGE = ">>>>>>>>>>>>>>DELETE<<<<<<<<<<<<<<<"


def ensure_hyperlint_dir() -> Path:
    """
    Create the .hyperlint directory if it doesn't exist and return its path.
    """
    hyperlint_dir = Path.cwd() / ".hyperlint"
    if not hyperlint_dir.exists():
        hyperlint_dir.mkdir(exist_ok=True)
        logger.info(f"Created .hyperlint directory at {hyperlint_dir}")

    # Create approvals directory
    approvals_dir = hyperlint_dir / "approvals"
    if not approvals_dir.exists():
        approvals_dir.mkdir(exist_ok=True)
        logger.info(f"Created approvals directory at {approvals_dir}")

    return hyperlint_dir


def get_issue_type(issue) -> str:
    """
    Return the issue type as a string for logging purposes.
    """
    if isinstance(issue, ReplaceLineFixableIssue):
        return "replacement"
    elif isinstance(issue, InsertLineIssue):
        return "insertion"
    elif isinstance(issue, DeleteLineIssue):
        return "deletion"
    else:
        return "unknown"


class FixedLine(BaseModel):
    "The fix for a given line of content. It must include the entire line replaced, not just the partial fix."

    replacement_content: str = Field(description="The replacement content for the line")


class LineIssue(BaseModel):
    line: int
    issue_message: List[str]


class ReplaceLineFixableIssue(LineIssue):
    existing_content: str

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
{issues_str}
</issue>

Rewrite the entire line resolving the issue description. It is imperative to rewrite the entire line, even if the issue appears in a single word or part of the line. We are going to replace the entire above line so you must maintain the original line except for the fixes to the issues.
"""

            # Call Anthropic API
            print(prompt)
            message = patched_client.chat.completions.create(
                model="anthropic/claude-3-haiku-20240307",
                max_tokens=4096,
                temperature=0.25,
                messages=[{"role": "user", "content": prompt}],
                response_model=FixedLine,
            )

            # Match indentation of original content
            leading_spaces = len(self.existing_content) - len(
                self.existing_content.lstrip()
            )
            return " " * leading_spaces + message.replacement_content.lstrip()

        except Exception as e:
            logger.error(f"Error fixing line issue: {e}")
            return self.existing_content


class InsertLineIssue(BaseModel):
    line: int
    insert_content: str


class DeleteLineIssue(ReplaceLineFixableIssue):
    def fix(self) -> str:
        return DELETE_LINE_MESSAGE


def log_approval_decision(
    issue_type: str,
    issue: Union[ReplaceLineFixableIssue, InsertLineIssue, DeleteLineIssue],
    approved: bool,
    fix: Optional[str] = None,
    file_path: Optional[str] = None,
) -> None:
    """
    Log the approval decision to a JSONL file.

    Args:
        issue_type: Type of issue (replacement, insertion, deletion)
        issue: The issue object
        approved: Whether the fix was approved
        fix: The proposed fix (for replacements)
        file_path: The path to the file being edited
    """
    # Create log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "file": str(file_path),
        "line": issue.line,
        "approved": approved,
    }

    # Add issue-specific details
    if isinstance(issue, ReplaceLineFixableIssue):
        log_entry["issue_message"] = issue.issue_message
        log_entry["content_before"] = issue.existing_content
        log_entry["content_after"] = fix
    elif isinstance(issue, InsertLineIssue):
        log_entry["content_after"] = issue.insert_content
    elif isinstance(issue, DeleteLineIssue):
        log_entry["issue_message"] = issue.issue_message
        log_entry["content_before"] = issue.existing_content

    # Ensure .hyperlint directory exists
    hyperlint_dir = ensure_hyperlint_dir()
    approvals_dir = hyperlint_dir / "approvals"

    # Create log file path
    log_file = approvals_dir / f"{issue_type}.jsonl"

    # Append to log file
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    logger.debug(f"Logged {issue_type} approval decision to {log_file}")


def prompt_for_approval(
    issue: Union[ReplaceLineFixableIssue, InsertLineIssue, DeleteLineIssue],
    proposed_fix: Optional[str] = None,
    file_path: Optional[str] = None,
) -> bool:
    """
    Prompt the user to approve a proposed fix.

    Args:
        issue: The issue object to be fixed
        proposed_fix: The proposed fix (for replacements)
        file_path: The path to the file being edited

    Returns:
        bool: True if approved, False otherwise
    """
    console = Console()

    file_info = f"File: {file_path}" if file_path else ""
    line_info = f"Line: {issue.line}"

    if isinstance(issue, ReplaceLineFixableIssue):
        issue_msg = (
            "\n".join(issue.issue_message)
            if isinstance(issue.issue_message, list)
            else issue.issue_message
        )

        console.print(
            Panel.fit(
                f"{file_info}\n{line_info}\n\n[bold]Issue:[/bold]\n{issue_msg}\n\n"
                f"[bold]Original:[/bold]\n{Syntax(issue.existing_content, 'markdown', theme='monokai')}\n\n"
                f"[bold]Proposed fix:[/bold]\n{Syntax(proposed_fix, 'markdown', theme='monokai')}",
                title="[bold green]Replacement Needed[/bold green]",
                border_style="green",
            )
        )

    elif isinstance(issue, InsertLineIssue):
        console.print(
            Panel.fit(
                f"{file_info}\n{line_info}\n\n"
                f"[bold]Proposed insertion:[/bold]\n{Syntax(issue.insert_content, 'markdown', theme='monokai')}",
                title="[bold blue]Insertion Needed[/bold blue]",
                border_style="blue",
            )
        )

    elif isinstance(issue, DeleteLineIssue):
        issue_msg = (
            "\n".join(issue.issue_message)
            if isinstance(issue.issue_message, list)
            else issue.issue_message
        )

        console.print(
            Panel.fit(
                f"{file_info}\n{line_info}\n\n[bold]Issue:[/bold]\n{issue_msg}\n\n"
                f"[bold]Content to delete:[/bold]\n{Syntax(issue.existing_content, 'markdown', theme='monokai')}",
                title="[bold red]Deletion Needed[/bold red]",
                border_style="red",
            )
        )

    return console.input(
        "\n[bold]Apply this change? [y/n]:[/bold] "
    ).lower().strip() in ("y", "yes")


class BaseEditor(ABC, BaseModel):
    path: FilePath
    text: str | None = None
    replacements: List[ReplaceLineFixableIssue] = Field(
        default_factory=list, repr=False
    )
    insertions: List[InsertLineIssue] = Field(default_factory=list, repr=False)
    deletions: List[DeleteLineIssue] = Field(default_factory=list, repr=False)
    require_approval: bool = True
    log_approvals: bool = True

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
        return OrderedDict(
            (line_number, line_content)
            for line_number, line_content in enumerate(self.get_text().split("\n"), 1)
        )

    def get_text_with_line_numbers(self) -> str:
        return "\n".join(
            [
                f"{line_number}: {line_content}"
                for line_number, line_content in self.get_line_number_lookup().items()
            ]
        )

    def generate_v2(self) -> str:
        # Ensure text is loaded
        self.get_text()
        # Let subclass populate the issues
        self.collect_issues()

        initial_line_lookup = self.get_line_number_lookup()
        changes: Dict[int, str] = {}  # Store results of fixes/deletions
        # Compress issues by line number
        compressed_issues: Dict[int, List[ReplaceLineFixableIssue]] = {}
        for issue in self.replacements:
            if issue.line not in compressed_issues:
                compressed_issues[issue.line] = []
            compressed_issues[issue.line].append(issue)

        # Process all issues for each line
        for line_no, line_issues in compressed_issues.items():
            combined_content = initial_line_lookup[line_no]
            for issue in line_issues:
                proposed_fix = issue.fix()

                # Request approval if required
                approved = True
                if self.require_approval:
                    approved = prompt_for_approval(
                        issue=issue, proposed_fix=proposed_fix, file_path=str(self.path)
                    )

                # Log decision if enabled
                if self.log_approvals:
                    log_approval_decision(
                        issue_type=get_issue_type(issue),
                        issue=issue,
                        approved=approved,
                        fix=proposed_fix,
                        file_path=str(self.path),
                    )

                # Apply the fix if approved
                if approved:
                    combined_content = proposed_fix
                    logger.success(f"Approved replacement for line {line_no}")
                else:
                    logger.warning(f"Rejected replacement for line {line_no}")

            if combined_content != initial_line_lookup[line_no]:
                changes[line_no] = combined_content
                logger.success(
                    f"Replacing line {line_no} with content: {combined_content}"
                )

        # Process deletions
        for issue in self.deletions:
            # Request approval if required
            approved = True
            if self.require_approval:
                approved = prompt_for_approval(issue=issue, file_path=str(self.path))

            # Log decision if enabled
            if self.log_approvals:
                log_approval_decision(
                    issue_type=get_issue_type(issue),
                    issue=issue,
                    approved=approved,
                    file_path=str(self.path),
                )

            # Apply the deletion if approved
            if approved:
                changes[issue.line] = DELETE_LINE_MESSAGE  # Mark for deletion
                logger.warning(f"Deleting line {issue.line}: {issue.existing_content}")
            else:
                logger.warning(f"Rejected deletion for line {issue.line}")

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

                # Request approval if required
                approved = True
                if self.require_approval:
                    approved = prompt_for_approval(
                        issue=insert_issue, file_path=str(self.path)
                    )

                # Log decision if enabled
                if self.log_approvals:
                    log_approval_decision(
                        issue_type=get_issue_type(insert_issue),
                        issue=insert_issue,
                        approved=approved,
                        file_path=str(self.path),
                    )

                # Apply the insertion if approved
                if approved:
                    final_lines.append(insert_issue.insert_content)
                    logger.info(
                        f"Inserting before line {line_no}: {insert_issue.insert_content}"
                    )
                else:
                    logger.warning(f"Rejected insertion before line {line_no}")

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

            # Request approval if required
            approved = True
            if self.require_approval:
                approved = prompt_for_approval(
                    issue=insert_issue, file_path=str(self.path)
                )

            # Log decision if enabled
            if self.log_approvals:
                log_approval_decision(
                    issue_type=get_issue_type(insert_issue),
                    issue=insert_issue,
                    approved=approved,
                    file_path=str(self.path),
                )

            # Apply the insertion if approved
            if approved:
                logger.info(
                    f"Inserting after last line ({insert_issue.line}): {insert_issue.insert_content}"
                )
                final_lines.append(insert_issue.insert_content)
            else:
                logger.warning(
                    f"Rejected insertion after last line ({insert_issue.line})"
                )

            insertion_idx += 1

        self.text = "\n".join(final_lines)
        return self.get_text()

    def update_file(self):
        path = self.path
        final_content = self.generate_v2()

        with open(path, "w") as f:
            f.write(final_content)

        return path

    def dry_run(self):
        path = self.path
        original_text = self.get_text()
        final_content = self.generate_v2()

        difflib.unified_diff(original_text.splitlines(), final_content.splitlines())
        print(final_content)
        return path
