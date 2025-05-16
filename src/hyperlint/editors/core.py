import difflib
import json
from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime
from typing import Dict, List, Optional, Union

import instructor
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field, FilePath
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from ..config import DEFAULT_EDIT_MODEL, DELETE_LINE_MESSAGE, SimpleConfig

patched_client = instructor.from_litellm(completion=completion)


def diff(old: str, new: str):
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
    )
    return "\n".join(diff)


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

    def fix(self, context: str | None = None) -> str:
        """
        Fix the line issue using Anthropic's API.

        Returns:
            The corrected line as a string, or the original line if fixing failed.
        """

        try:
            issues_str = "\n".join(self.issue_message)
            logger.debug(f"Fixing line issue: {issues_str}")
            context_str = ""
            if context:
                context_str = (
                    "Here is some context around the line in question\n<context>\n"
                    + context
                    + "\n</context>\n"
                )

            # Prepare prompt for Anthropic
            prompt = f"""Act as if you are a professional editor with 3 years of experience.

{context_str}
Rewrite the following line:

<line number={self.line}>
{self.existing_content}
</line>

To fix the following issue:

<issue>
{issues_str}
</issue>

Rewrite the entire line resolving the issue description. It is imperative to rewrite the entire line, even if the issue appears in a single word or part of the line. We are going to replace the entire above line so you must maintain the original line except for the fixes to the issues.
"""

            message = patched_client.chat.completions.create(
                model=DEFAULT_EDIT_MODEL,
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


class DeleteLineIssue(LineIssue):
    existing_content: str
    
    def fix(self) -> str:
        return DELETE_LINE_MESSAGE


def log_approval_decision(
    issue_type: str,
    issue: Union[ReplaceLineFixableIssue, InsertLineIssue, DeleteLineIssue],
    approved: bool,
    fix: Optional[str] = None,
    file_path: Optional[str] = None,
    config: Optional[SimpleConfig] = None,
) -> None:
    """
    Log the approval decision to a JSONL file.

    Args:
        issue_type: Type of issue (replacement, insertion, deletion)
        issue: The issue object
        approved: Whether the fix was approved
        fix: The proposed fix (for replacements)
        file_path: The path to the file being edited
        config: Configuration object (uses default if None)
    """
    # Use default config if none provided
    if config is None:
        config = SimpleConfig()
        
    # Create log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "file": str(file_path),
        "issue_type": issue_type,
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

    # Ensure hyperlint directory exists
    config.ensure_storage_dir()
    approvals_dir = config.get_judge_data_dir()

    # Create log file path
    log_file = approvals_dir / "changes.jsonl"

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
        # Create syntax objects

        console.print(
            Panel.fit(
                f"{file_info}\n{line_info}\n\n[bold]Issue:[/bold]\n{issue_msg}\n\n"
                f"[bold]Original:[/bold]",
                title="[bold green]Replacement Needed[/bold green]",
                border_style="green",
            )
        )
        # Display the original and proposed fix side by side
        original_text = Text(f"- {issue.existing_content}", style="red")
        proposed_text = Text(f"+ {proposed_fix}", style="green")
        console.print("Line {0}:".format(issue.line), style="bold")
        console.print(Columns([original_text, proposed_text]))
    elif isinstance(issue, InsertLineIssue):
        # Create syntax object for the insertion
        insertion_syntax = Syntax(issue.insert_content, "markdown", theme="monokai")

        console.print(
            Panel.fit(
                f"{file_info}\n{line_info}\n\n[bold]Proposed insertion:[/bold]",
                title="[bold blue]Insertion Needed[/bold blue]",
                border_style="blue",
            )
        )
        console.print(insertion_syntax)

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
    config: SimpleConfig = Field(default_factory=lambda: SimpleConfig())
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
        logger.debug(f"Adding replacement issue: {issue}")
        self.replacements.append(issue)

    def add_insertion(self, issue: InsertLineIssue):
        logger.debug(f"Adding insertion issue: {issue}")
        self.insertions.append(issue)

    def add_deletion(self, issue: DeleteLineIssue):
        logger.debug(f"Adding deletion issue: {issue}")
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

    def _approval_filter(
        self,
        issue: ReplaceLineFixableIssue | DeleteLineIssue | InsertLineIssue,
        proposed_fix: str,
    ) -> bool:
        if self.config.dry_run:
            logger.debug("Is dry run, approving")
            return True
        if not self.config.approval_mode:
            logger.debug("does not require approval")
            return True

        approved = prompt_for_approval(
            issue=issue, proposed_fix=proposed_fix, file_path=str(self.path)
        )

        # Log decision if enabled
        if self.config.log_approvals:
            log_approval_decision(
                issue_type=get_issue_type(issue),
                issue=issue,
                approved=approved,
                fix=proposed_fix,
                file_path=str(self.path),
                config=self.config,
            )

        return approved

    def _compress_issues(self):
        # Compress issues by line number
        compressed_issues: Dict[int, List[ReplaceLineFixableIssue]] = {}
        for issue in self.replacements:
            if issue.line not in compressed_issues:
                compressed_issues[issue.line] = []
            compressed_issues[issue.line].append(issue)

        logger.debug(
            f"Compressed {len(self.replacements)} into {len(compressed_issues)}"
        )
        return compressed_issues

    def _get_surrounding_lines(
        self, line_number: int, line_count: int, line_lookup: Dict[int, str]
    ) -> List[str]:
        # Get surrounding lines for a given line number
        surrounding_lines: List[str] = []
        # Determine the range of lines to include
        start_line = max(1, line_number - line_count)
        end_line = line_number + line_count + 1

        # Collect all lines in range
        for line_no in range(start_line, end_line):
            if line_no in line_lookup:
                surrounding_lines.append(f"{line_no}: {line_lookup[line_no]}")

        return surrounding_lines

    def generate_v2(self) -> str:
        self.get_text()
        self.collect_issues()
        compressed_issues = self._compress_issues()
        initial_line_lookup = self.get_line_number_lookup()
        changes: Dict[int, str] = {}  # Store results of fixes/deletions

        # Process all issues for each line
        for line_no, line_issues in compressed_issues.items():
            issues = list(
                set([msg for issue in line_issues for msg in issue.issue_message])
            )
            logger.debug(f"Fixing {len(issues)} issues on line {line_no}")
            deduped_issue = line_issues[0]
            deduped_issue.issue_message = issues
            context = "\n".join(
                self._get_surrounding_lines(line_no, 5, initial_line_lookup)
            )
            proposed_fix = deduped_issue.fix(context)
            approved = self._approval_filter(deduped_issue, proposed_fix)
            if approved and proposed_fix != initial_line_lookup[line_no]:
                changes[line_no] = proposed_fix
                initial_line_lookup[line_no] = proposed_fix

        # Process deletions
        for issue in self.deletions:
            approved = self._approval_filter(issue, "TO DELETE")
            if approved:
                changes[issue.line] = DELETE_LINE_MESSAGE
                initial_line_lookup[issue.line] = (
                    DELETE_LINE_MESSAGE  # Mark for deletion
                )

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
                approved = self._approval_filter(
                    insert_issue, insert_issue.insert_content
                )
                # Apply the insertion if approved
                if approved:
                    final_lines.append(insert_issue.insert_content)

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

            approved = self._approval_filter(insert_issue, insert_issue.insert_content)
            if approved:
                final_lines.append(insert_issue.insert_content)

            insertion_idx += 1

        self.text = "\n".join(final_lines)
        return self.get_text()

    def update_file(self):
        path = self.path
        original_text = self.get_text()
        final_content = self.generate_v2()

        console = Console()
        old_lines = original_text.splitlines()
        new_lines = final_content.splitlines()

        # Display the diff manually
        for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines)):
            if old_line != new_line:
                console.print(f"Line {i + 1}:", style="bold")
                old_text = Text(f"- {old_line}", style="red")
                new_text = Text(f"+ {new_line}", style="green")
                console.print(Columns([old_text, new_text]))
        approved = console.input(
            "\n[bold]Update the file? [y/n]:[/bold] "
        ).lower().strip() in ("y", "yes")

        if approved:
            with open(path, "w") as f:
                f.write(final_content)

        return path

    def dry_run(self):
        # Ensure dry run mode is active
        old_dry_run = self.config.dry_run
        self.config.dry_run = True
        
        path = self.path
        original_text = self.get_text()
        final_content = self.generate_v2()
        print(diff(original_text, final_content))
        
        # Restore original dry run setting
        self.config.dry_run = old_dry_run
        return path
