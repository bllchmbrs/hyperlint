# tests/unit/media_generators/test_image_generator.py
import os
from pathlib import Path
import pytest # For capsys and fixtures
from unittest.mock import patch, MagicMock

from hyperlint.media_generators.image_generator import ImageGenerator

class TestImageGenerator:
    @patch('tempfile.NamedTemporaryFile')
    def test_generate_placeholder(self, mock_named_temp_file, capsys):
        # Configure the mock for NamedTemporaryFile
        # It needs to simulate the context manager protocol (__enter__, __exit__)
        # and provide a 'name' attribute for the dummy file path.
        mock_file_object = MagicMock()
        mock_file_object.name = "dummy_image.png" # Controlled temporary file name
        
        mock_temp_file_context_manager = MagicMock()
        mock_temp_file_context_manager.__enter__.return_value = mock_file_object
        mock_temp_file_context_manager.__exit__.return_value = None # Or False
        
        mock_named_temp_file.return_value = mock_temp_file_context_manager

        # Mock Path().write_text in case the placeholder tries to write something,
        # although the current one doesn't. For robustness.
        # Also, we need to mock Path(dummy_file_path).exists() to return True,
        # as the file won't actually be created by the mocked tempfile.
        # However, the current implementation of ImageGenerator.generate doesn't check for existence itself.
        # It only creates a file. The test will verify if the *returned path* seems correct.
        # The actual file creation is mocked, so os.remove or Path.unlink would fail.
        # The key benefit of mocking tempfile is to avoid actual file I/O during unit tests.

        generator = ImageGenerator()
        generated_files = generator.generate()

        # 1. Assert that the method returns a list containing one string
        assert isinstance(generated_files, list)
        assert len(generated_files) == 1
        
        file_path_str = generated_files[0]
        assert isinstance(file_path_str, str)
        
        # 2. Assert that the file specified by the returned path has a .png extension
        # (using the controlled name from the mock)
        file_path = Path(file_path_str)
        assert file_path.name == "dummy_image.png" # Check the name we set in the mock
        assert file_path.suffix == ".png"

        # 3. Assert tempfile.NamedTemporaryFile was called correctly
        mock_named_temp_file.assert_called_once_with(suffix=".png", delete=False)

        # 4. Capture stdout to assert that the placeholder message is printed
        captured = capsys.readouterr()
        assert f"ImageGenerator: Placeholder - Created dummy image file: {file_path_str}" in captured.out

        # 5. Cleanup: Not strictly necessary to os.remove when tempfile.NamedTemporaryFile
        # is fully mocked, as no file is actually created on the filesystem.
        # If we were testing the unmocked version, os.remove would be here.
        # For example, if we wanted to test the actual file creation:
        # Path(file_path_str).unlink(missing_ok=True) 
        # But with the mock, this isn't needed.

    def test_generate_placeholder_os_error(self, capsys):
        """
        Test that generate handles an OSError during tempfile creation gracefully.
        """
        with patch('tempfile.NamedTemporaryFile', side_effect=OSError("Disk full")):
            generator = ImageGenerator()
            generated_files = generator.generate()

            assert isinstance(generated_files, list)
            assert len(generated_files) == 0 # Should return an empty list on error

            captured = capsys.readouterr()
            assert "ImageGenerator: Placeholder - Error creating dummy file: Disk full" in captured.out
