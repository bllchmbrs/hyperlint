import base64
import os
import shutil
import tempfile
from typing import List

import dspy
from loguru import logger
from openai import OpenAI
from rich.console import Console
from rich.prompt import Confirm

from .core import BaseEditor, ReplaceLineFixableIssue

client = OpenAI()

check_and_revise_prompt = dspy.Predict(
    "desired_prompt: str, current_image: dspy.Image, current_prompt:str -> feedback:str, image_strictly_matches_desired_prompt: bool, revised_prompt: str"
)


def generate_image(prompt: str, path: str):
    result = client.images.generate(model="dall-e-3", prompt=prompt)
    print(result)

    if result.data:
        image_base64 = result.data[0].b64_json
        if image_base64:
            image_bytes = base64.b64decode(image_base64)

            # Save the image to a file
            with open(path, "wb") as f:
                f.write(image_bytes)
            return

    logger.warning("Failed to generate image")


class ImageGenerator:
    def __init__(self, text: str):
        self.text = text
        self.temp_dir = tempfile.mkdtemp()

    def __del__(self):
        """Clean up the temporary directory when the instance is destroyed"""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def iterate_on_image(self, initial_prompt: str):
        """Generate images based on prompts derived from the text"""

        console = Console()
        image_paths = []
        current_prompt = initial_prompt
        iteration = 0

        while True:
            # Create a unique filename for each image
            image_path = os.path.join(self.temp_dir, f"image_{iteration}.png")
            generate_image(current_prompt, image_path)

            # Add the path to our list if the file was created
            if os.path.exists(image_path):
                image_paths.append(image_path)

                # Ask user if the image is good enough
                console.print(f"Generated image with prompt: {current_prompt}")
                console.print(f"Image saved at: {image_path}")

                if Confirm.ask("Is this image good enough?"):
                    return [image_path]  # Return only the final acceptable image

                # If not good enough, use dspy to revise the prompt
                try:
                    # Load the image for dspy to analyze
                    current_image = dspy.Image.from_file(image_path)

                    # Get feedback and revised prompt
                    result = check_and_revise_prompt(
                        desired_prompt=initial_prompt,
                        current_image=current_image,
                        current_prompt=current_prompt,
                    )

                    console.print(f"[yellow]Feedback: {result.feedback}[/yellow]")
                    current_prompt = result.revised_prompt
                    console.print(f"[green]Revised prompt: {current_prompt}[/green]")

                except Exception as e:
                    console.print(f"[red]Error in prompt revision: {str(e)}[/red]")
                    # If revision fails, ask the user for a new prompt
                    from rich.prompt import Prompt

                    current_prompt = Prompt.ask(
                        "Enter a revised prompt", default=current_prompt
                    )

            iteration += 1

        return image_paths

    def get_concepts(self):
        """Extract concepts from the text that can be used as image prompts"""
        # This is a placeholder implementation
        # In a real implementation, you might use NLP or other techniques
        # to extract meaningful concepts from the text

        # For now, just return the text as a single concept
        return [self.text]


class ImageEditor(BaseEditor):
    """
    Editor for handling image-related editing tasks.
    Uses ImageApprovalLog for approvals that may involve image display.
    """

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
            line=line, issue_message=message, existing_content=content
        )
        self.add_replacement(issue)
