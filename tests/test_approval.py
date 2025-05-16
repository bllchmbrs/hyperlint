import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path

from hyperlint.approval import (
    ApprovalLog,
    EditorApprovalLog,
    ConsoleEditorApprovalLog,
    ImageApprovalLog,
    SilentApprovalLog,
    get_approval_log
)
from hyperlint.config import SimpleConfig
from hyperlint.editors.core import ReplaceLineFixableIssue, InsertLineIssue, DeleteLineIssue


class TestApprovalLog(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for test logs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = SimpleConfig(
            hyperlint_dir=Path(self.temp_dir.name)
        )

    def tearDown(self):
        # Clean up temporary directory
        self.temp_dir.cleanup()

    def test_factory_function(self):
        """Test that the factory function returns the correct implementation"""
        # Test default (console)
        approval_log = get_approval_log(self.config)
        self.assertIsInstance(approval_log, ConsoleEditorApprovalLog)
        
        # Test image
        approval_log = get_approval_log(self.config, approval_type="image")
        self.assertIsInstance(approval_log, ImageApprovalLog)
        
        # Test silent
        approval_log = get_approval_log(self.config, approval_type="silent")
        self.assertIsInstance(approval_log, SilentApprovalLog)
        
        # Test config-based type
        self.config.approval_type = "image"
        approval_log = get_approval_log(self.config)
        self.assertIsInstance(approval_log, ImageApprovalLog)
        
        # Test dry run override
        self.config.dry_run = True
        approval_log = get_approval_log(self.config, approval_type="console")
        self.assertIsInstance(approval_log, SilentApprovalLog)

    @patch('rich.console.Console.input')
    def test_console_approval_prompt(self, mock_input):
        """Test that console approval correctly handles user input"""
        # Set up mock
        mock_input.return_value = "y"
        
        # Create test objects
        approval_log = ConsoleEditorApprovalLog(self.config)
        issue = ReplaceLineFixableIssue(
            line=10, 
            issue_message=["Test issue"],
            existing_content="Test content"
        )
        
        context = {
            'issue': issue,
            'proposed_fix': "Fixed content",
            'file_path': "test.py"
        }
        
        # Test approval
        result = approval_log.prompt_for_approval(context)
        self.assertTrue(result)
        mock_input.assert_called_once()
        
        # Test rejection
        mock_input.return_value = "n"
        mock_input.reset_mock()
        result = approval_log.prompt_for_approval(context)
        self.assertFalse(result)
        mock_input.assert_called_once()

    def test_silent_approval(self):
        """Test that silent approval always returns True"""
        approval_log = SilentApprovalLog(self.config)
        issue = DeleteLineIssue(
            line=15,
            issue_message=["Delete this line"],
            existing_content="Content to delete"
        )
        
        context = {
            'issue': issue,
            'file_path': "test.py"
        }
        
        result = approval_log.prompt_for_approval(context)
        self.assertTrue(result)

    def test_log_decision(self):
        """Test that decisions are correctly logged"""
        approval_log = SilentApprovalLog(self.config)
        issue = InsertLineIssue(
            line=20,
            insert_content="New content to insert"
        )
        
        context = {
            'issue': issue,
            'file_path': "test.py"
        }
        
        # Log a decision
        approval_log.log_decision("insertion", context, True)
        
        # Check that log file was created
        log_path = approval_log.get_log_file_path()
        self.assertTrue(log_path.exists())
        
        # Check log content
        with open(log_path, 'r') as f:
            log_content = f.read()
            self.assertIn("insertion", log_content)
            self.assertIn("test.py", log_content)
            self.assertIn("New content to insert", log_content)
            self.assertIn("true", log_content.lower())  # JSON boolean


if __name__ == '__main__':
    unittest.main()