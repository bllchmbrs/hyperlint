import json
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod

from rich.console import Console
from rich.prompt import Confirm
from rich.prompt import Prompt as RichPrompt # Alias for clarity

from .models import MediaApproval

class ApprovalLog(ABC):
    """Abstract base class for an approval log."""

    @abstractmethod
    def log_approval(self, approval_data: MediaApproval) -> None:
        pass

    @abstractmethod
    def get_log_file_path(self) -> Path:
        pass

    @abstractmethod
    def prompt_for_approval(self, approval_request: MediaApproval) -> bool:
        pass

class MediaApprovalLog(ApprovalLog):
    """Logging system for media generation approvals."""

    def __init__(self, log_file_name: str = "media_approvals.jsonl", config=None):
        self._log_file_name = log_file_name
        self.config = config # Placeholder for actual config object/system
        self.console = Console()

    def get_log_file_path(self) -> Path:
        """Get path to media approval log file."""
        if self.config and hasattr(self.config, "get_judge_data_dir"):
            return self.config.get_judge_data_dir() / self._log_file_name
        else:
            log_dir = Path.home() / ".media_assistant_logs"
            return log_dir / self._log_file_name

    def log_approval(self, approval_data: MediaApproval) -> None:
        """Logs the approval data to a JSONL file."""
        log_path_val = self.get_log_file_path() # Renamed variable
        log_path_val.parent.mkdir(parents=True, exist_ok=True)

        try:
            log_entry = approval_data.model_dump_json()
        except AttributeError:
            log_entry = json.dumps(approval_data.dict())

        with open(log_path_val, "a") as f:
            f.write(log_entry + "\n") # Keeping \n as per prior instruction, will test this
        
        # Using {{log_path_val}} for f-string within f-string style escaping for subtask
        self.console.print(f"Approval decision logged to [cyan]{{log_path_val}}[/cyan]")


    def prompt_for_approval(self, approval_request: MediaApproval) -> bool:
        """
        Displays information about the generated media and prompts the user for approval.
        Updates the approval_request object with the user's decision and feedback.
        """
        self.console.print("\n--- Media Approval Request ---")
        # Using {{...}} for f-string within f-string style escaping for subtask
        self.console.print(f"Media Type: {{approval_request.media_type}}")
        self.console.print(f"File Path: [blue]{{approval_request.file_path}}[/blue]")
        self.console.print(f"Original Prompt: {{approval_request.original_prompt}}")
        self.console.print(f"Refined Prompt: {{approval_request.refined_prompt}}")
        if approval_request.context_text:
            self.console.print(f"Context: {{approval_request.context_text}}")

        self.console.print(
            "[yellow]Please review the media at the path shown above.[/yellow]"
        )

        approved = Confirm.ask("Approve this media?", default=True)
        approval_request.approved = approved
        
        feedback_text: Optional[str] = None
        if not approved:
            feedback_text = RichPrompt.ask("Provide feedback/reason for rejection (optional)", default="")
            approval_request.feedback = feedback_text if feedback_text else "Rejected without detailed feedback."
        else:
            approval_request.feedback = "Approved"

        self.log_approval(approval_request)

        return approved
