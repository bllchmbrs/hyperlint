# tests/unit/media_generators/test_base.py
import pytest # Pytest is commonly used, good to import if needed, though not strictly for these model tests
from typing import Optional, Dict, Any # For type hinting if constructing complex test data

from hyperlint.media_generators.base import MediaGenerationResult

class TestMediaGenerationResult:
    def test_creation_with_required_fields(self):
        result = MediaGenerationResult(
            file_path="/path/to/file.png",
            prompt="A cat",
            task="image_generation",
            approved=True
        )
        assert result.file_path == "/path/to/file.png"
        assert result.prompt == "A cat"
        assert result.task == "image_generation"
        assert result.approved is True
        assert result.feedback is None # Default value for Optional field
        assert result.metadata == {}   # Default value for metadata

    def test_creation_with_all_fields(self):
        result = MediaGenerationResult(
            file_path="/path/to/image.jpg",
            prompt="A dog playing fetch",
            task="image_gen",
            approved=False,
            feedback="Image too blurry",
            metadata={"engine": "dall-e-3", "size": "1024x1024"}
        )
        assert result.file_path == "/path/to/image.jpg"
        assert result.prompt == "A dog playing fetch"
        assert result.task == "image_gen"
        assert result.approved is False
        assert result.feedback == "Image too blurry"
        assert result.metadata == {"engine": "dall-e-3", "size": "1024x1024"}

    def test_creation_metadata_defaults_to_empty_dict(self):
        """Explicitly tests that metadata defaults to an empty dict."""
        result = MediaGenerationResult(
            file_path="/path/to/another.gif",
            prompt="A funny gif",
            task="gif_creation",
            approved=True
            # metadata is omitted
        )
        assert result.metadata == {}
        assert result.feedback is None # Also check feedback default again for good measure
        
    def test_optional_feedback_provided(self):
        """Tests creation with feedback provided and metadata omitted."""
        result = MediaGenerationResult(
            file_path="/path/to/sound.mp3",
            prompt="Ocean waves",
            task="audio_generation",
            approved=True,
            feedback="Sounds great!"
            # metadata is omitted
        )
        assert result.file_path == "/path/to/sound.mp3"
        assert result.prompt == "Ocean waves"
        assert result.task == "audio_generation"
        assert result.approved is True
        assert result.feedback == "Sounds great!"
        assert result.metadata == {}

    def test_optional_metadata_provided(self):
        """Tests creation with metadata provided and feedback omitted."""
        result = MediaGenerationResult(
            file_path="/path/to/video.mp4",
            prompt="City skyline",
            task="video_generation",
            approved=False,
            metadata={"resolution": "1080p", "fps": 30}
            # feedback is omitted
        )
        assert result.file_path == "/path/to/video.mp4"
        assert result.prompt == "City skyline"
        assert result.task == "video_generation"
        assert result.approved is False
        assert result.feedback is None
        assert result.metadata == {"resolution": "1080p", "fps": 30}
