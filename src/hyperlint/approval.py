import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import BaseModel
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from .config import SimpleConfig


class ApprovalRequest(BaseModel):
    approved: bool


class EditorApprovalRequest(BaseModel):
    file_path: Path
    issue_type: str
    line: int
    issue_messages: str
    existing_content: str | None
    replacement_content: str | None

    model_config = {"json_encoders": {Path: str}}


class EditorApproval(ApprovalRequest, EditorApprovalRequest):
    pass


class MediaApproval(ApprovalRequest):
    original_prompt: str
    refined_prompt: str
    context_text: str
    media_type: str
    feedback: Optional[str] = None
    file_path: Path

    model_config = {"json_encoders": {Path: str}}


class ApprovalLog(ABC):
    """
    Abstract base class for approval logging interfaces.
    Generic implementation that can handle different types of approval scenarios.
    """

    def __init__(self, config: SimpleConfig):
        """
        Initialize the approval log with an optional configuration.

        Args:
            config: Configuration settings, using SimpleConfig defaults if not provided
        """
        self.config = config
        self.decision_type = "editor"

    @abstractmethod
    def prompt_for_approval(self, *args, **kwargs) -> bool:
        """
        Prompt the user to approve a proposed action.

        Args:
            context: A dictionary containing all relevant information for the approval

        Returns:
            bool: True if approved, False otherwise
        """
        pass

    def log_decision(self, approval: ApprovalRequest) -> None:
        """
        Log the approval decision.

        Args:
            approval: ApprovalRequest object containing the decision and context
        """
        # Ensure hyperlint directory exists
        self.config.ensure_storage_dirs()
        log_entry = approval.model_dump()
        log_entry["date"] = datetime.now().isoformat()
        # Ensure file_path is a string for JSON serialization if it exists
        if "file_path" in log_entry and isinstance(log_entry["file_path"], Path):
            log_entry["file_path"] = str(log_entry["file_path"])

        # Get log file path and write to it
        log_file = self.get_log_file_path()
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        logger.debug(f"Logged {self.decision_type} approval decision to {log_file}")

    @abstractmethod
    def get_log_file_path(self) -> Path:
        """
        Get the path to the log file for this approval log.
        Each subclass should implement this to define its own log file location.

        Returns:
            Path to the log file
        """
        pass


class EditorApprovalLog(ApprovalLog):
    """
    Approval log specifically for text editing operations.
    Handles replacements, insertions, and deletions.
    """

    def __init__(self, config: SimpleConfig):
        super().__init__(config)
        self.decision_type = "editor"

    def prompt_for_approval(self, approval_request: EditorApprovalRequest) -> bool:
        """
        Prompt the user to approve a proposed edit.

        Args:
            approval_request: EditorApprovalRequest object containing:
                - file_path: Path to the file being edited
                - issue_type: Type of issue (replacement, insertion, deletion)
                - line: Line number where the issue occurs
                - issue_messages: Description of the issue
                - existing_content: Current content (for replacements and deletions)
                - replacement_content: Proposed new content (for replacements and insertions)

        Returns:
            bool: True if approved, False otherwise
        """

        file_info = (
            f"File: {approval_request.file_path}" if approval_request.file_path else ""
        )
        line_info = f"Line: {approval_request.line}"
        issue_messages = approval_request.issue_messages
        console = Console()
        console.print("Hello")

        if approval_request.issue_type in ("replace", "delete"):
            console.print(
                Panel.fit(
                    f"{file_info}\n{line_info}\n\n[bold]Issue:[/bold]\n{issue_messages}\n\n"
                    f"[bold]Original:[/bold]",
                    title="[bold green]Replacement Needed[/bold green]",
                    border_style="green",
                )
            )
            # Display the original and proposed fix side by side
            original_text = Text(f"- {approval_request.existing_content}", style="red")
            proposed_text = Text(
                f"+ {approval_request.replacement_content}", style="green"
            )
            console.print("Line {0}:".format(approval_request.line), style="bold")
            console.print(Columns([original_text, proposed_text]))
        elif approval_request.issue_type == "insert":
            # Create syntax object for the insertion
            insertion_syntax = Syntax(
                approval_request.replacement_content or "", "markdown", theme="monokai"
            )

            console.print(
                Panel.fit(
                    f"{file_info}\n{line_info}\n\n[bold]Proposed insertion:[/bold]",
                    title="[bold blue]Insertion Needed[/bold blue]",
                    border_style="blue",
                )
            )
            console.print(insertion_syntax)

        approved = console.input(
            "\n[bold]Apply this change? [y/n]:[/bold] "
        ).lower().strip() in ("y", "yes")

        # Log the decision
        editor_approval = EditorApproval(
            **approval_request.model_dump(), approved=approved
        )
        self.log_decision(editor_approval)

        return approved

    def get_log_file_path(self) -> Path:
        """Get the path to the editor approval log file"""
        self.config.ensure_storage_dirs()
        return self.config.get_judge_data_dir() / "editor_judge.jsonl"


class MediaApprovalLog(ApprovalLog):
    """
    Approval log specifically for media generation operations.
    """

    def __init__(self, config: SimpleConfig):
        super().__init__(config)
        self.decision_type = "media"

    def prompt_for_approval(self, approval_request: MediaApproval) -> bool:
        """
        Prompt the user to approve a generated media.

        Args:
            approval_request: MediaApproval object containing:
                - original_prompt: The initial prompt for media generation
                - refined_prompt: The refined prompt used for media generation
                - context_text: Text context used for media generation
                - media_type: Type of media (e.g., "image", "audio")
                - file_path: Path to the generated media file

        Returns:
            bool: True if approved, False otherwise
        """
        console = Console()

        console.print(
            Panel.fit(
                f"[bold]Media Type:[/bold] {approval_request.media_type}\n"
                f"[bold]File Path:[/bold] {approval_request.file_path}\n\n"
                f"[bold]Original Prompt:[/bold]\n{approval_request.original_prompt}\n\n"
                f"[bold]Refined Prompt:[/bold]\n{approval_request.refined_prompt}\n\n"
                f"[bold]Context Text:[/bold]\n{approval_request.context_text}",
                title="[bold blue]Media Approval Needed[/bold blue]",
                border_style="blue",
            )
        )

        approved_input = console.input(
            "\n[bold]Approve this media? [y/n]:[/bold] "
        ).lower().strip()
        approved = approved_input in ("y", "yes")

        # Create a new MediaApproval instance that includes the decision
        # This is because the approval_request passed in doesn't have the 'approved' field set yet.
        # self.log_decision expects it.
        final_approval_decision = MediaApproval(
            **approval_request.model_dump(exclude={"approved", "feedback"}),  # Exclude existing approved/feedback if any
            approved=approved,
            feedback=approval_request.feedback # Preserve original feedback if any, or allow new later
        )
        # Log the decision
        self.log_decision(final_approval_decision)

        return approved

    def get_log_file_path(self) -> Path:
        """Get the path to the media approval log file"""
        self.config.ensure_storage_dirs()
        return self.config.get_judge_data_dir() / "media_approvals.jsonl"
