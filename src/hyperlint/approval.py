import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

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
    def prompt_for_approval(self, context) -> bool:
        """
        Prompt the user to approve a proposed action.

        Args:
            context: A dictionary containing all relevant information for the approval

        Returns:
            bool: True if approved, False otherwise
        """
        pass

    def log_decision(self, decision_type: str, context: dict, approved: bool) -> None:
        """
        Log the approval decision.

        Args:
            decision_type: Type of decision (e.g., "edit", "create", "delete")
            context: A dictionary containing all relevant information about the decision
            approved: Whether the action was approved
        """
        # Ensure hyperlint directory exists
        self.config.ensure_storage_dirs()
        
        # Convert context to a JSON-serializable format
        serializable_context = {}
        for key, value in context.items():
            if hasattr(value, 'model_dump'):  # Pydantic object
                serializable_context[key] = value.model_dump()
            else:
                serializable_context[key] = value
        
        log_entry = {
            "decision_type": decision_type,
            "approved": approved,
            "date": datetime.now().isoformat(),
            "file_path": str(context.get("file_path", "")),
            "context": serializable_context
        }

        # Get log file path and write to it
        log_file = self.get_log_file_path()
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        logger.debug(f"Logged {decision_type} approval decision to {log_file}")

    @abstractmethod
    def get_log_file_path(self) -> Path:
        """
        Get the path to the log file for this approval log.
        Each subclass should implement this to define its own log file location.

        Returns:
            Path to the log file
        """
        pass


class ConsoleEditorApprovalLog(ApprovalLog):
    """
    Console-based approval log specifically for text editing operations.
    Handles replacements, insertions, and deletions.
    """

    def __init__(self, config: SimpleConfig):
        super().__init__(config)
        self.decision_type = "editor"

    def prompt_for_approval(self, context) -> bool:
        """
        Prompt the user to approve a proposed edit.

        Args:
            context: A dictionary containing:
                - issue: Issue object (ReplaceLineFixableIssue, DeleteLineIssue, InsertLineIssue)
                - proposed_fix: The proposed fix content
                - file_path: Path to the file being edited

        Returns:
            bool: True if approved, False otherwise
        """
        issue = context.get('issue')
        proposed_fix = context.get('proposed_fix')
        file_path = context.get('file_path')

        file_info = f"File: {file_path}" if file_path else ""
        line_info = f"Line: {issue.line}"
        console = Console()

        if hasattr(issue, 'existing_content'):  # Replace or Delete issue
            issue_messages = "\n".join(issue.issue_message) if hasattr(issue, 'issue_message') else "Issue detected"
            console.print(
                Panel.fit(
                    f"{file_info}\n{line_info}\n\n[bold]Issue:[/bold]\n{issue_messages}\n\n"
                    f"[bold]Original:[/bold]",
                    title="[bold green]Change Needed[/bold green]",
                    border_style="green",
                )
            )
            # Display the original and proposed fix side by side
            original_text = Text(f"- {issue.existing_content}", style="red")
            proposed_text = Text(f"+ {proposed_fix}", style="green")
            console.print("Line {0}:".format(issue.line), style="bold")
            console.print(Columns([original_text, proposed_text]))
        elif hasattr(issue, 'insert_content'):  # Insert issue
            # Create syntax object for the insertion
            insertion_syntax = Syntax(
                proposed_fix or "", "markdown", theme="monokai"
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
        self.log_decision(self.decision_type, context, approved)

        return approved

    def get_log_file_path(self) -> Path:
        """Get the path to the editor approval log file"""
        self.config.ensure_storage_dirs()
        return self.config.get_judge_data_dir() / "editor_judge.jsonl"


class EditorApprovalLog(ConsoleEditorApprovalLog):
    """
    Alias for ConsoleEditorApprovalLog for backward compatibility.
    """
    pass


class SilentApprovalLog(ApprovalLog):
    """
    Silent approval log that always approves without user interaction.
    Useful for dry runs and automated processing.
    """

    def __init__(self, config: SimpleConfig):
        super().__init__(config)
        self.decision_type = "silent"

    def prompt_for_approval(self, context) -> bool:
        """
        Always approve without prompting the user.
        
        Args:
            context: A dictionary containing approval context
            
        Returns:
            bool: Always True
        """
        # Log the decision
        self.log_decision(self.decision_type, context, True)
        
        return True

    def get_log_file_path(self) -> Path:
        """Get the path to the silent approval log file"""
        self.config.ensure_storage_dirs()
        return self.config.get_judge_data_dir() / "silent_judge.jsonl"


class ImageApprovalLog(ApprovalLog):
    """
    Image-based approval log for visual approval workflows.
    """

    def __init__(self, config: SimpleConfig):
        super().__init__(config)
        self.decision_type = "image"

    def prompt_for_approval(self, context) -> bool:
        """
        Placeholder for image-based approval.
        Currently falls back to console approval.
        
        Args:
            context: A dictionary containing approval context
            
        Returns:
            bool: Approval decision
        """
        # For now, fall back to console approval
        console_log = ConsoleEditorApprovalLog(self.config)
        return console_log.prompt_for_approval(context)

    def get_log_file_path(self) -> Path:
        """Get the path to the image approval log file"""
        self.config.ensure_storage_dirs()
        return self.config.get_judge_data_dir() / "image_judge.jsonl"


def get_approval_log(config: SimpleConfig, approval_type: str | None = None) -> ApprovalLog:
    """
    Factory function to create the appropriate approval log instance.
    
    Args:
        config: SimpleConfig instance
        approval_type: Type of approval log ("console", "image", "silent", None)
                      If None, uses config.approval_type or defaults to "console"
                      
    Returns:
        ApprovalLog: The appropriate approval log instance
    """
    # Check for dry run override
    if config.dry_run:
        return SilentApprovalLog(config)
    
    # Determine approval type
    if approval_type is None:
        approval_type = getattr(config, 'approval_type', 'console')
    
    if approval_type == "silent":
        return SilentApprovalLog(config)
    elif approval_type == "image":
        return ImageApprovalLog(config)
    else:  # Default to console
        return ConsoleEditorApprovalLog(config)
