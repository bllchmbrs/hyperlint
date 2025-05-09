import os
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from editai.editors.folder_processor import FolderProcessor
from editai.editors.core import BaseEditor


class MockEditor(BaseEditor):
    """Mock editor for testing the folder processor."""
    
    def prerun_checks(self) -> bool:
        return True
    
    def collect_issues(self) -> None:
        # Mock implementation - just append a marker to the content
        pass
    
    def generate_v2(self) -> str:
        # Mock implementation - just append a marker to the content
        content = self.get_text()
        return f"{content}\n<!-- Processed by MockEditor -->"


class TestFolderProcessor(TestCase):
    """Tests for the FolderProcessor class."""
    
    def setUp(self):
        """Set up a temporary directory with test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        
        # Create test files
        self.md_files = []
        for i in range(3):
            file_path = self.test_dir / f"test{i}.md"
            with open(file_path, "w") as f:
                f.write(f"# Test Document {i}\n\nThis is test document {i}.")
            self.md_files.append(file_path)
        
        # Create a non-markdown file
        self.txt_file = self.test_dir / "test.txt"
        with open(self.txt_file, "w") as f:
            f.write("This is not a markdown file.")
        
        # Create a subdirectory with more files
        self.subdir = self.test_dir / "subdir"
        self.subdir.mkdir()
        self.subdir_files = []
        for i in range(2):
            file_path = self.subdir / f"subtest{i}.md"
            with open(file_path, "w") as f:
                f.write(f"# Subdir Test Document {i}\n\nThis is subdir test document {i}.")
            self.subdir_files.append(file_path)
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def test_process_directory_non_recursive(self):
        """Test processing a directory without recursion."""
        processor = FolderProcessor(
            directory_path=self.test_dir,
            editor_class=MockEditor,
            recursive=False
        )
        
        results = processor.process_directory(dry_run=True)
        
        # Should find only the markdown files in the top directory
        self.assertEqual(len(results), 3)
        for file_path in self.md_files:
            self.assertIn(file_path, results)
            self.assertIn("<!-- Processed by MockEditor -->", results[file_path])
        
        # Should not include subdirectory files
        for file_path in self.subdir_files:
            self.assertNotIn(file_path, results)
    
    def test_process_directory_recursive(self):
        """Test processing a directory with recursion."""
        processor = FolderProcessor(
            directory_path=self.test_dir,
            editor_class=MockEditor,
            recursive=True
        )
        
        results = processor.process_directory(dry_run=True)
        
        # Should find all markdown files, including those in subdirectories
        self.assertEqual(len(results), 5)
        for file_path in self.md_files + self.subdir_files:
            self.assertIn(file_path, results)
            self.assertIn("<!-- Processed by MockEditor -->", results[file_path])
    
    def test_include_pattern(self):
        """Test using an include pattern to filter files."""
        processor = FolderProcessor(
            directory_path=self.test_dir,
            editor_class=MockEditor,
            include_pattern="test1*.md",  # Only include files starting with test1
            recursive=True
        )
        
        results = processor.process_directory(dry_run=True)
        
        # Should only find test1.md
        self.assertEqual(len(results), 1)
        self.assertIn(self.test_dir / "test1.md", results)
    
    def test_exclude_patterns(self):
        """Test using exclude patterns to filter files."""
        processor = FolderProcessor(
            directory_path=self.test_dir,
            editor_class=MockEditor,
            exclude_patterns=["*1.md", "subdir/*"],  # Exclude all files with 1 in name and all in subdir
            recursive=True
        )
        
        results = processor.process_directory(dry_run=True)
        
        # Should find test0.md and test2.md, but not test1.md or any in subdir
        self.assertEqual(len(results), 2)
        self.assertIn(self.test_dir / "test0.md", results)
        self.assertIn(self.test_dir / "test2.md", results)
        self.assertNotIn(self.test_dir / "test1.md", results)
        for file_path in self.subdir_files:
            self.assertNotIn(file_path, results)
    
    def test_dry_run_mode(self):
        """Test that dry run mode doesn't modify files."""
        # Read the original content
        original_contents = {}
        for file_path in self.md_files:
            with open(file_path, "r") as f:
                original_contents[file_path] = f.read()
        
        processor = FolderProcessor(
            directory_path=self.test_dir,
            editor_class=MockEditor,
            recursive=False
        )
        
        # Process in dry run mode
        processor.process_directory(dry_run=True)
        
        # Check that files are unchanged
        for file_path in self.md_files:
            with open(file_path, "r") as f:
                current_content = f.read()
            self.assertEqual(current_content, original_contents[file_path])
    
    def test_actual_modification(self):
        """Test that files are actually modified when not in dry run mode."""
        processor = FolderProcessor(
            directory_path=self.test_dir,
            editor_class=MockEditor,
            recursive=False
        )
        
        # Process without dry run
        processor.process_directory(dry_run=False)
        
        # Check that files are modified
        for file_path in self.md_files:
            with open(file_path, "r") as f:
                content = f.read()
            self.assertIn("<!-- Processed by MockEditor -->", content)
    
    @mock.patch('editai.editors.folder_processor.logger')
    def test_error_handling(self, mock_logger):
        """Test that errors are handled gracefully."""
        # Create a problematic file
        error_file = self.test_dir / "error.md"
        with open(error_file, "w") as f:
            f.write("# Error file")
        
        # Create a mock editor that raises an exception
        class ErrorEditor(BaseEditor):
            def prerun_checks(self) -> bool:
                return True
            
            def collect_issues(self) -> None:
                pass
            
            def generate_v2(self) -> str:
                raise ValueError("Test error")
        
        processor = FolderProcessor(
            directory_path=self.test_dir,
            editor_class=ErrorEditor,
            include_pattern="error.md",
            recursive=False
        )
        
        # Process should not raise an exception
        results = processor.process_directory(dry_run=True)
        
        # Should be empty because the error was caught
        self.assertEqual(len(results), 0)
        
        # Logger should have been called with an error message
        mock_logger.error.assert_called_once()
        self.assertIn("Error processing file", mock_logger.error.call_args[0][0])