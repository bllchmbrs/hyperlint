# tests/unit/media_generators/test_mermaid_generator.py
import os
from pathlib import Path
import pytest # For capsys and fixtures
from unittest.mock import patch, MagicMock

from hyperlint.media_generators.mermaid_generator import MermaidDiagramGenerator

class TestMermaidDiagramGenerator:
    @patch('tempfile.NamedTemporaryFile')
    def test_generate_placeholder(self, mock_named_temp_file, capsys):
        # Configure the mock for NamedTemporaryFile
        mock_file_object = MagicMock()
        mock_file_object.name = "dummy_diagram.mmd" # Controlled temporary file name
        
        mock_temp_file_context_manager = MagicMock()
        mock_temp_file_context_manager.__enter__.return_value = mock_file_object
        mock_temp_file_context_manager.__exit__.return_value = None # Or False
        
        mock_named_temp_file.return_value = mock_temp_file_context_manager

        generator = MermaidDiagramGenerator()
        generated_files = generator.generate()

        # 1. Assert that the method returns a list containing one string
        assert isinstance(generated_files, list)
        assert len(generated_files) == 1
        
        file_path_str = generated_files[0]
        assert isinstance(file_path_str, str)
        
        # 2. Assert that the file specified by the returned path has a .mmd extension
        file_path = Path(file_path_str)
        assert file_path.name == "dummy_diagram.mmd" # Check the name we set in the mock
        assert file_path.suffix == ".mmd"

        # 3. Assert tempfile.NamedTemporaryFile was called correctly
        mock_named_temp_file.assert_called_once_with(suffix=".mmd", delete=False)

        # 4. Capture stdout to assert that the placeholder message is printed
        captured = capsys.readouterr()
        assert f"MermaidDiagramGenerator: Placeholder - Created dummy diagram file: {file_path_str}" in captured.out

        # 5. Cleanup: Not strictly necessary as tempfile.NamedTemporaryFile is mocked.

    def test_generate_placeholder_os_error(self, capsys):
        """
        Test that generate handles an OSError during tempfile creation gracefully.
        """
        with patch('tempfile.NamedTemporaryFile', side_effect=OSError("No space left on device")):
            generator = MermaidDiagramGenerator()
            generated_files = generator.generate()

            assert isinstance(generated_files, list)
            assert len(generated_files) == 0 # Should return an empty list on error

            captured = capsys.readouterr()
            assert "MermaidDiagramGenerator: Placeholder - Error creating dummy file: No space left on device" in captured.out
