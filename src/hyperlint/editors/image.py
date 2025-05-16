import base64
from typing import List

from loguru import logger
from openai import OpenAI
from pydantic import FilePath

from ..config import SimpleConfig
from ..approval import get_approval_log
from .core import BaseEditor, ReplaceLineFixableIssue

client = OpenAI()


def generate_image(prompt: str, config: SimpleConfig):
    result = client.images.generate(model="gpt-image-1", prompt=prompt)

    if result.data:
        image_base64 = result.data[0].b64_json
        if image_base64:
            image_bytes = base64.b64decode(image_base64)

            # Save the image to a file
            with open("otter.png", "wb") as f:
                f.write(image_bytes)
            return

    logger.warning("Failed to generate image")


class ImageEditor(BaseEditor):
    """
    Editor for handling image-related editing tasks.
    Uses ImageApprovalLog for approvals that may involve image display.
    """
    
    def __init__(self, path: FilePath, **kwargs):
        # Initialize with ImageApprovalLog
        super().__init__(
            path=path, 
            approval_log=get_approval_log(
                kwargs.get("config", SimpleConfig()), 
                approval_type="image"
            ),
            **kwargs
        )
    
    def prerun_checks(self) -> bool:
        # Placeholder implementation
        return True
        
    def collect_issues(self) -> None:
        # Placeholder implementation for collecting image-related issues
        logger.info("Image editor doesn't have any issues to collect yet")
        pass
        
    def add_image_related_issue(self, line: int, message: List[str], content: str):
        """
        Add a custom image-related issue that will use the ImageApprovalLog
        
        Args:
            line: Line number in the file
            message: List of issue messages
            content: Current content that needs modification
        """
        issue = ReplaceLineFixableIssue(
            line=line,
            issue_message=message,
            existing_content=content
        )
        self.add_replacement(issue)
