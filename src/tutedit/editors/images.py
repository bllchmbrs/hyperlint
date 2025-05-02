import base64
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import diskcache  # type: ignore
import instructor

# litellm imports
import litellm
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field, FilePath

# Import from .core and potentially other project utils
from .core import (
    BaseEditor,
    DeleteLineIssue,
    InsertLineIssue,
    ReplaceLineFixableIssue,
)

# Constants
cache = diskcache.Cache("./data/cache/image_editor")
patched_client = instructor.from_litellm(completion=completion)


class ImageCaption(BaseModel):
    """Represents the generated caption for an image."""

    caption: str = Field(description="The generated image caption.")


class ImageName(BaseModel):
    """Represents the generated name for an image."""

    name: str = Field(description="The generated image name.")


class InsertLocation(BaseModel):
    """Represents the line number where the image should be inserted."""

    line_number: int = Field(description="The line number for image insertion.")


class ImageAmbles(BaseModel):
    """Represents the preamble and postamble text for an image."""

    preamble: str = Field(description="The preamble text introducing the image.")
    postamble: str = Field(
        description="The postamble text transitioning from the image."
    )


class InternalImage(BaseModel):
    """Represents an image file found for the article."""

    path: Path

    def _get_image_content(self, b64_encode: bool = True) -> str | bytes:
        """Reads image content, optionally base64 encoding it."""
        try:
            with open(self.path, "rb") as f:
                content = f.read()
                if b64_encode:
                    return base64.b64encode(content).decode("utf-8")
                else:
                    return content
        except FileNotFoundError:
            logger.error(f"Image file not found: {self.path}")
            return "" if b64_encode else b""
        except Exception as e:
            logger.error(f"Error reading image {self.path}: {e}")
            return "" if b64_encode else b""

    @cache.memoize()
    def _generate_image_caption(self) -> str:
        """Generates a caption (alt text) for the image using an AI model."""
        image_content = self._get_image_content()
        if not image_content or not isinstance(image_content, str):
            return ""

        try:
            prompt = """Please provide a concise alt text description for this image, suitable for use in an HTML `alt` attribute. Be descriptive but brief.
            """

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",  # Assuming PNG
                                "data": image_content,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            response: ImageCaption = patched_client(
                model="claude-3-haiku-20240307",
                max_tokens=400,
                messages=messages,
                response_model=ImageCaption,
            )

            logger.success(
                f"Generated image caption for {self.path}: {response.caption}"
            )
            return response.caption

        except Exception as e:
            logger.error(
                f"Error generating image caption for {self.path}: {e}", exc_info=True
            )
            return ""

    @cache.memoize()
    def _generate_image_name(self) -> str:
        """Generates a sanitized file name for the image using an AI model."""
        image_content = self._get_image_content()
        if not image_content or not isinstance(image_content, str):
            return ""

        try:
            prompt = """Please provide a concise, descriptive, lowercase file name for this image, suitable for web use.

            Some tips:
            - Use a short, descriptive name (3-5 words max)
            - Use only lowercase letters and underscores (no spaces or other special characters)
            - Do not include the file extension.
            """

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",  # Assuming PNG
                                "data": image_content,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            response: ImageName = patched_client(
                model="claude-3-haiku-20240307",
                max_tokens=400,
                messages=messages,
                response_model=ImageName,
            )

            name = response.name.strip().lower().replace(" ", "_")
            # Basic sanitization
            name = re.sub(r"[^\w_]+", "", name)
            # Add extension
            _, ext = os.path.splitext(self.path)
            if not ext:
                ext = ".png"  # Default extension
            final_name = f"{name}{ext}"
            logger.success(f"Generated image name for {self.path}: {final_name}")
            return final_name

        except Exception as e:
            logger.error(
                f"Error generating image name for {self.path}: {e}", exc_info=True
            )
            return ""

    @cache.memoize()
    def get_insert_location(
        self,
        text_with_line_numbers: str,
        blacklist_locations: List[int],
        extra_prompt: str = "",
    ) -> int:
        """Determines the line number where the image should be inserted."""
        image_content = self._get_image_content()
        if not image_content or not isinstance(image_content, str):
            return -1

        prompt = (
            f"""
        You are an expert technical writer assisting in placing an image within an article.
        Analyze the provided text (with line numbers) and the image (shown previously). Determine the single most appropriate line number *after which* to insert this image.

        Here is the text with line numbers:
        <text>
        {text_with_line_numbers}
        </text>

        CRITICAL: Do NOT select any of the following line numbers, as they are already occupied or blacklisted:
        <blacklist_locations>
        {", ".join(map(str, blacklist_locations))}
        </blacklist_locations>

        Consider these factors before deciding:
        - Logical flow: Where does the image best fit to illustrate a concept, introduce a section, or provide context?
        - Relevance: Insert the image near the text it directly relates to.
        - Placement: Generally, images should appear *after* introductory text or a paragraph explaining them, and *before* the detailed content (like code blocks) they illustrate. Avoid placing the image as the very first element.
        - Reader experience: How will placing the image here help the reader understand the content better?

        First, explain your reasoning within <thinking> tags. Then, provide the chosen line number in <line_number> tags.
        """
            + extra_prompt
        )

        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",  # Assuming PNG
                                "data": image_content,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            response: InsertLocation = patched_client(
                model="claude-3-opus-20240229",  # Using Opus for potentially better reasoning
                max_tokens=500,
                messages=messages,
                response_model=InsertLocation,
            )

            line_number = response.line_number
            if line_number in blacklist_locations:
                logger.warning(
                    f"AI chose blacklisted line {line_number} for {self.path}. Retrying.",
                )
                # Simple retry mechanism (could be more robust)
                return self.get_insert_location(
                    text_with_line_numbers,
                    blacklist_locations,
                    " PREVIOUS ATTEMPT FAILED: The line number chosen was blacklisted. Please choose a DIFFERENT line number.",
                )
            logger.success(
                f"Determined insert location for {self.path}: after line {line_number}"
            )
            return line_number

        except Exception as e:
            logger.error(
                f"Error getting insert location for {self.path}: {e}", exc_info=True
            )
            return -1

    @cache.memoize()
    def get_ambles(
        self, text_with_line_numbers: str, caption: str, line_number: int
    ) -> Tuple[str, str]:
        """Generates preamble and postamble text for the image using an AI model."""
        image_content = self._get_image_content()
        if not image_content or not isinstance(image_content, str):
            return "", ""

        try:
            # Rough context extraction (adjust window size as needed)
            context_window = 5
            lines = text_with_line_numbers.splitlines()
            start_line = max(0, line_number - context_window)
            end_line = min(len(lines), line_number + context_window + 1)
            context_text = "\n".join(lines[start_line:end_line])

            prompt = f"""You are an expert technical writer. Given an image (shown previously), its caption ("{caption}"), the line number ({line_number}) where it will be inserted, and the surrounding text context, please write:
            1. A concise preamble (1-2 sentences) to introduce the image. Explain its relevance or what the reader should focus on.
            2. A concise postamble (1 sentence) to transition smoothly from the image to the following text.

            Context (Image will be inserted after line {line_number}):
            <text_context>
            {context_text}
            </text_context>

            Image Caption: {caption}

            Guidelines:
            - Keep ambles brief and natural-sounding.
            - The preamble should precede the image markdown.
            - The postamble should follow the image markdown.
            - If either amble is unnecessary or doesn't make sense, return empty strings.
            """

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",  # Assuming PNG
                                "data": image_content,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            response: ImageAmbles = patched_client(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=messages,
                response_model=ImageAmbles,
            )

            preamble = response.preamble.strip()
            postamble = response.postamble.strip()

            logger.success(
                f"Generated ambles for {self.path}: Preamble='{preamble}', Postamble='{postamble}'"
            )
            return preamble, postamble

        except Exception as e:
            logger.error(f"Error generating ambles for {self.path}: {e}", exc_info=True)
            return "", ""

    def as_insert_line_issues(
        self,
        text_with_line_numbers: str,
        blacklist_locations: List[int],
        image_url_prefix: str,
    ) -> List[InsertLineIssue]:
        """Generates InsertLineIssue objects for the image and its ambles."""
        insert_issues: List[InsertLineIssue] = []

        # 1. Determine insert location
        # Add current potential insertion points to blacklist temporarily to avoid collisions during generation
        temp_blacklist = list(
            set(blacklist_locations + [i for i in range(1, 5)])
        )  # Include first few lines too
        line_number = self.get_insert_location(text_with_line_numbers, temp_blacklist)
        if line_number == -1:
            logger.warning(
                f"Could not determine insert location for {self.path}. Skipping."
            )
            return []

        # 2. Generate caption and new filename
        caption = self._generate_image_caption()
        if not caption:
            logger.warning(
                f"Could not generate caption for {self.path}. Using filename as fallback."
            )
            caption = os.path.splitext(os.path.basename(self.path))[0].replace(
                "_", " "
            )  # Fallback caption

        new_image_name = self._generate_image_name()
        if not new_image_name:
            logger.error(
                f"Could not generate new name for {self.path}. Cannot create insertion."
            )
            return []  # Cannot insert without a valid name/URL

        # 3. Generate ambles
        preamble, postamble = self.get_ambles(
            text_with_line_numbers, caption, line_number
        )

        # 4. Create InsertLineIssue objects (order matters for application)
        # Insertions happen *after* the specified line number.
        # We want: Preamble -> Image -> Postamble

        insertion_point = (
            line_number  # All insertions happen relative to this original line
        )

        # Add Preamble (if exists) - inserts after line `insertion_point`
        if preamble:
            insert_issues.append(
                InsertLineIssue(line=insertion_point, insert_content=preamble)
            )
            insertion_point += 1  # Next insertion point shifts down

        # Add Image Markdown - inserts after the original line (or preamble if it existed)
        image_markdown = (
            f"![{caption}]({image_url_prefix.rstrip('/')}/{new_image_name})"
        )
        insert_issues.append(
            InsertLineIssue(line=insertion_point, insert_content=image_markdown)
        )
        insertion_point += 1  # Next insertion point shifts down

        # Add Postamble (if exists) - inserts after the image markdown
        if postamble:
            insert_issues.append(
                InsertLineIssue(line=insertion_point, insert_content=postamble)
            )
            # insertion_point += 1 # Not needed for subsequent images in loop

        logger.info(
            f"Prepared {len(insert_issues)} insertions for image {self.path} at line {line_number}"
        )
        return insert_issues


class ImageAdditionEditor(BaseEditor):
    """
    Editor that finds images associated with an article, generates captions and names,
    determines optimal insertion points, and generates markdown insertions with ambles.
    """

    image_url_prefix: str = Field(
        default="/images",
        description="The URL prefix for image paths in the markdown output.",
    )
    image_folder_path: Path = Field(
        description="The path to the subfolder containing images within the article directory.",
    )

    def _get_image_dir(self) -> Optional[str]:
        """Locates the directory containing images for the article."""
        try:
            # Use the potentially imported get_directory function

            image_dir = str(self.image_folder_path)
            if self.image_folder_path.is_dir():
                logger.info(f"Found image directory: {self.image_folder_path}")
                return str(self.image_folder_path)
            else:
                logger.warning(
                    f"Image directory not found at expected location: {self.image_folder_path}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting images for title '{self.path}': {e}")
            return None

    def _prepare_images(self, image_dir: str) -> List[InternalImage]:
        """Creates InternalImage objects and handles renaming/copying."""
        image_objects: List[InternalImage] = []
        copied_files = (
            set()
        )  # Track successfully copied files to avoid processing originals if copy fails

        try:
            image_files_paths = [
                p
                for p in Path(image_dir).iterdir()
                if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif")
            ]
            image_files = [p.name for p in image_files_paths]
        except FileNotFoundError:
            logger.error(f"Cannot list files, image directory not found: {image_dir}")
            return []
        except Exception as e:
            logger.error(f"Error listing files in image directory {image_dir}: {e}")
            return []

        logger.info(f"Found {len(image_files)} potential image files in {image_dir}")

        for file_path_obj in image_files_paths:
            original_path_str = str(file_path_obj)
            image = InternalImage(path=file_path_obj)
            new_name = image._generate_image_name()

            if new_name:
                new_path_obj = file_path_obj.parent / new_name
                new_path_str = str(new_path_obj)
                if original_path_str.lower() != new_path_str.lower():  # Avoid self-copy
                    try:
                        shutil.copy2(
                            original_path_str, new_path_str
                        )  # shutil usually works fine with str
                        logger.success(
                            f"Copied '{original_path_str}' to '{new_path_str}'"
                        )
                        # Use the new path for the InternalImage object
                        image.path = new_path_obj
                        copied_files.add(
                            new_path_str
                        )  # Add the *new* path string if needed
                        image_objects.append(image)
                    except Exception as e:
                        logger.error(
                            f"Failed to copy '{original_path_str}' to '{new_path_str}': {e}"
                        )
                        # If copy fails, should we still process the original? Maybe not.
                else:
                    # Name generated is the same as original, use original path
                    logger.info(
                        f"Generated name '{new_name}' matches original '{file_path_obj.name}'. Using original."
                    )
                    image_objects.append(image)  # Use original image object
            else:
                logger.warning(
                    f"Could not generate name for '{original_path_str}'. Skipping this image."
                )

        # Log summary
        processed_count = len(image_objects)
        skipped_count = (
            len(image_files) - processed_count
        )  # Approximation if copies failed
        logger.success(
            f"Prepared {processed_count} images for processing. Skipped {skipped_count}."
        )
        return image_objects

    def prerun_checks(self) -> bool:
        """Checks if necessary configurations and directories exist."""
        # Removed anthropic key check
        image_dir = self._get_image_dir()
        if image_dir is None:
            # Logged in _get_image_dir, returning True to allow editor to run (but do nothing)
            return True
        return True

    def collect_issues(self) -> None:
        """Finds images, prepares them, determines locations, and adds insertion issues."""
        image_dir = self._get_image_dir()
        if not image_dir:
            return

        # Prepare images (includes renaming/copying)
        image_objects = self._prepare_images(image_dir)
        if not image_objects:
            logger.info("No images found or prepared. No insertions to generate.")
            return

        text_with_line_numbers = self.get_text_with_line_numbers()  # Use helper method

        # Keep track of lines where insertions *will* happen to avoid conflicts between images
        # Includes line itself and potentially +/- 1 for ambles
        blacklist_locations: List[int] = [0, 1, 2, 3]  # Initial blacklist
        insertions_count = 0

        for image in image_objects:
            # Pass the current blacklist to the image processing method
            current_image_insertions = image.as_insert_line_issues(
                text_with_line_numbers, blacklist_locations, self.image_url_prefix
            )

            if current_image_insertions:
                # Sort insertions for this specific image before adding
                # This ensures ambles and image are added in the correct order relative to each other
                sorted_current_insertions = sorted(
                    current_image_insertions, key=lambda issue: issue.line
                )

                for issue in sorted_current_insertions:
                    self.add_insertion(issue)  # Add to the BaseEditor's list
                    insertions_count += 1

                # Update blacklist with the lines affected by these insertions
                # The insertion line numbers are relative to the *original* document state
                # before these insertions are applied.
                affected_lines = {issue.line for issue in current_image_insertions}
                # Also blacklist lines around the core image insertion for safety
                # Find the core image insertion line (heuristic: middle issue)
                if len(current_image_insertions) > 0:
                    core_line = sorted([i.line for i in current_image_insertions])[
                        len(current_image_insertions) // 2
                    ]
                    affected_lines.add(core_line - 1)
                    affected_lines.add(core_line + 1)

                blacklist_locations.extend(list(affected_lines))
                # Remove duplicates and sort for cleaner logging/debugging
                blacklist_locations = sorted(list(set(blacklist_locations)))

        logger.success(
            f"Collected a total of {insertions_count} line insertions for {len(image_objects)} images."
        )
        # No need to return anything or sort globally here, BaseEditor handles processing order
