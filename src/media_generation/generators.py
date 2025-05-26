import base64
import os
import shutil
import tempfile
from typing import List, Optional
from abc import ABC, abstractmethod
from pathlib import Path

import dspy  # type: ignore
from loguru import logger
from openai import OpenAI
from rich.console import Console
from rich.prompt import Prompt as RichPrompt

# Attempt to import dspy.Image specifically for type hinting if needed,
# and for direct use in from_file. DSPy's Predict signature parsing might handle it differently.
try:
    from dspy import Image as DSPyImage # Alias for clarity
except ImportError:
    logger.warning("dspy.Image could not be imported. DSPy image processing features might fail if not available in dspy module scope.")
    DSPyImage = None # Define as None if import fails

from .models import MediaApproval
from .approval import MediaApprovalLog

# --- OpenAI Client Initialization ---
try:
    client = OpenAI()
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}. Ensure OPENAI_API_KEY is set.")
    client = None

# --- DSPy Predictor Initialization ---
# Signature uses 'dspy.Image'. DSPy's Predict setup usually resolves this type string internally.
check_and_revise_prompt_signature = "desired_prompt: str, current_image: dspy.Image, current_prompt:str -> feedback:str, image_strictly_matches_desired_prompt: bool, revised_prompt: str"
try:
    check_and_revise_prompt = dspy.Predict(check_and_revise_prompt_signature)
except Exception as e:
    logger.error(f"Failed to initialize DSPy check_and_revise_prompt: {e}. Ensure DSPy is configured (e.g., dspy.settings.configure(lm=...)).")
    check_and_revise_prompt = None

# --- Helper Function for OpenAI Image Generation ---
def _generate_openai_image(prompt: str, file_path: str) -> bool:
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate image.")
        return False
    try:
        response = client.images.generate(
            model="dall-e-3",  # Consider making model configurable
            prompt=prompt,
            n=1,
            size="1024x1024",  # Consider making size configurable
            response_format="b64_json"
        )
        if response.data and response.data[0].b64_json:
            image_bytes = base64.b64decode(response.data[0].b64_json)
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"Image generated and saved to {file_path} with prompt: {prompt}")
            return True
        else:
            logger.warning(f"OpenAI image generation returned no data for prompt '{prompt}'.")
            return False
    except Exception as e:
        logger.error(f"OpenAI image generation failed for prompt '{prompt}': {e}")
    return False

# --- Abstract Base Class for Media Generation ---
class MediaGenerator(ABC):
    @abstractmethod
    def generate(self, initial_prompt: str, context_text: Optional[str] = None) -> List[str]:
        """
        Generate media content.
        Args:
            initial_prompt: The initial prompt for generation.
            context_text: Optional text providing context for the media.
        Returns:
            List[str]: Paths to generated and approved content files.
        """
        pass

# --- Concrete Image Generator Implementation ---
class ImageGenerator(MediaGenerator):
    def __init__(self, approval_log: Optional[MediaApprovalLog] = None, temp_dir_base: Optional[str] = None):
        self.console = Console()
        self.approval_log = approval_log if approval_log else MediaApprovalLog()
        
        self._temp_dir_base = Path(temp_dir_base) if temp_dir_base else None
        if self._temp_dir_base:
            self._temp_dir_base.mkdir(parents=True, exist_ok=True)
        self._owned_temp_dir = None # Stores TemporaryDirectory object if we create one

    def _get_temp_dir_path(self) -> Path:
        if self._temp_dir_base:
            # Create a unique subdirectory if a base is provided
            return Path(tempfile.mkdtemp(dir=self._temp_dir_base))
        else:
            # Create and manage an owned temporary directory
            if self._owned_temp_dir is None or not Path(self._owned_temp_dir.name).exists():
                self._owned_temp_dir = tempfile.TemporaryDirectory(prefix="image_gen_")
            return Path(self._owned_temp_dir.name)

    def __del__(self):
        if hasattr(self, '_owned_temp_dir') and self._owned_temp_dir:
            try:
                self._owned_temp_dir.cleanup()
                logger.info(f"Cleaned up temporary directory: {self._owned_temp_dir.name}")
            except Exception as e:
                logger.warning(f"Could not cleanup temporary directory {self._owned_temp_dir.name}: {e}")

    def generate(self, initial_prompt: str, context_text: Optional[str] = None) -> List[str]:
        if not client:
            self.console.print("[red]OpenAI client is not initialized. Cannot generate images.[/red]")
            return []
        
        dspy_ready = check_and_revise_prompt is not None
        if not dspy_ready:
            self.console.print("[yellow]Warning: DSPy prompt revision module is not available.[/yellow]")
            if dspy.settings.lm is None: # type: ignore
                 self.console.print("[yellow]Additionally, dspy.settings.lm is not configured, which is required for DSPy execution.[/yellow]")


        approved_image_paths: List[str] = []
        current_prompt = initial_prompt
        max_iterations = 5  # Make configurable?
        
        # Obtain a temporary directory path for this generation session
        # This path itself will be a unique dir per call to _get_temp_dir_path if base is used,
        # or the same owned dir if no base. For per-session, call it once.
        session_temp_dir = self._get_temp_dir_path()
        if not self._temp_dir_base: # if we own the dir, it's cleaned in __del__
            logger.info(f"Using owned temporary directory: {session_temp_dir}")
        else: # if using a base, this session_temp_dir is a subdir we might need to clean
            logger.info(f"Using session temporary directory: {session_temp_dir}")


        for iteration in range(1, max_iterations + 1):
            self.console.print(f"\n--- Iteration {iteration}/{max_iterations} ---")
            self.console.print(f"Current Prompt: [green]{current_prompt}[/green]")
            
            image_filename = f"image_iter_{iteration}.png"
            image_path = session_temp_dir / image_filename

            if not _generate_openai_image(current_prompt, str(image_path)):
                self.console.print("[red]OpenAI image generation failed.[/red]")
                if iteration == 1: break # Fail fast if first attempt fails
                # For subsequent failures, try user revision directly
                user_revised_prompt = RichPrompt.ask("OpenAI failed. Enter a new prompt or type 'abort'/'skip_dspy'", default=current_prompt)
                if user_revised_prompt.lower() == 'abort': break
                if user_revised_prompt.lower() == 'skip_dspy': continue # This will just retry OpenAI with same prompt unless user changes it
                current_prompt = user_revised_prompt
                continue

            approval_request = MediaApproval(
                file_path=str(image_path),
                original_prompt=initial_prompt,
                refined_prompt=current_prompt,
                context_text=context_text if context_text else "",
                media_type="image",
                approved=False,
                feedback=""
            )

            is_approved = self.approval_log.prompt_for_approval(approval_request)

            if is_approved:
                self.console.print(f"[green]Image approved: {image_path}[/green]")
                approved_image_paths.append(str(image_path))
                break 
            else:
                self.console.print(f"[yellow]Image rejected. Feedback: {approval_request.feedback}[/yellow]")
                if not dspy_ready:
                    self.console.print("[yellow]DSPy revision unavailable. Asking user for new prompt.[/yellow]")
                    user_revised_prompt = RichPrompt.ask("Enter a revised prompt or type 'abort'", default=current_prompt)
                    if user_revised_prompt.lower() == 'abort': break
                    current_prompt = user_revised_prompt
                    continue
                
                try:
                    if not DSPyImage: # Check if dspy.Image was imported
                        raise RuntimeError("DSPyImage class not available for image loading.")
                    if not os.path.exists(image_path): # Should exist, but check
                        raise FileNotFoundError(f"Image file {image_path} not found for DSPy revision.")
                        
                    current_dspy_image = DSPyImage.from_file(str(image_path))
                    
                    dspy_result = check_and_revise_prompt(
                        desired_prompt=initial_prompt, 
                        current_image=current_dspy_image,
                        current_prompt=current_prompt
                    )
                    
                    self.console.print(f"DSPy Feedback: [italic yellow]{dspy_result.feedback}[/italic yellow]") # type: ignore
                    current_prompt = dspy_result.revised_prompt # type: ignore
                    self.console.print(f"DSPy Revised Prompt: [green]{current_prompt}[/green]")

                except Exception as e:
                    self.console.print(f"[red]Error in DSPy prompt revision: {str(e)}[/red]")
                    user_revised_prompt = RichPrompt.ask("DSPy failed. Enter a revised prompt or type 'abort'", default=current_prompt)
                    if user_revised_prompt.lower() == 'abort': break
                    current_prompt = user_revised_prompt
            
            if iteration == max_iterations:
                self.console.print("[yellow]Reached maximum iterations.[/yellow]")
        
        if not approved_image_paths:
            self.console.print("[yellow]No image was approved.[/yellow]")

        # Cleanup for session_temp_dir if it's a subdir of a _temp_dir_base
        if self._temp_dir_base and session_temp_dir.exists():
            try:
                shutil.rmtree(session_temp_dir)
                logger.info(f"Cleaned up session temporary directory: {session_temp_dir}")
            except Exception as e:
                logger.warning(f"Could not cleanup session temporary directory {session_temp_dir}: {e}")
                
        return approved_image_paths

```
