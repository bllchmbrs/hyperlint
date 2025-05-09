import pytest
from pathlib import Path
from unittest import mock

from editai.editors.ai import AIEditor, LineEdit, LineEdits, CorrectedText


@pytest.fixture
def mock_line_edits():
    """Returns mock line edits for testing."""
    return LineEdits(
        line_edits=[
            LineEdit(
                starting_affected_line=1,
                ending_affected_line=1,
                issue_message="Title should be more descriptive",
                resolution="edit"
            ),
            LineEdit(
                starting_affected_line=3,
                ending_affected_line=3,
                issue_message="Redundant text",
                resolution="delete"
            ),
            LineEdit(
                starting_affected_line=5,
                ending_affected_line=6,
                issue_message="Complex formatting issue",
                resolution="flag"
            )
        ]
    )


class TestAIEditor:
    """Tests for the AIEditor class."""
    
    def test_prerun_checks(self, temp_markdown_file):
        """Test that prerun_checks always returns True."""
        editor = AIEditor(path=temp_markdown_file)
        
        result = editor.prerun_checks()
        
        assert result is True
    
    @mock.patch('editai.editors.ai.get_line_edits')
    def test_fetch_line_edits(self, mock_get_line_edits, temp_markdown_file, mock_line_edits):
        """Test that _fetch_line_edits calls get_line_edits with correct parameters."""
        mock_get_line_edits.return_value = mock_line_edits
        
        editor = AIEditor(path=temp_markdown_file)
        result = editor._fetch_line_edits()
        
        # Verify get_line_edits was called with text_with_line_numbers
        mock_get_line_edits.assert_called_once()
        
        # Verify the result is the mock_line_edits
        assert result == mock_line_edits
    
    @mock.patch('editai.editors.ai.get_line_edits')
    @mock.patch('editai.editors.ai.fix_line_edit')
    def test_collect_issues_with_edit(self, mock_fix_line_edit, mock_get_line_edits, 
                                      temp_markdown_file, mock_line_edits):
        """Test collect_issues with an edit resolution."""
        # Setup mock responses
        mock_get_line_edits.return_value = LineEdits(
            line_edits=[
                LineEdit(
                    starting_affected_line=1,
                    ending_affected_line=1,
                    issue_message="Title should be more descriptive",
                    resolution="edit"
                )
            ]
        )
        mock_fix_line_edit.return_value = "# Enhanced Test Document"
        
        editor = AIEditor(path=temp_markdown_file)
        editor.collect_issues()
        
        # Check that fix_line_edit was called
        mock_fix_line_edit.assert_called_once()
        
        # Verify that both insertion and deletion were created
        assert len(editor.insertions) == 1
        assert len(editor.deletions) == 1
        
        # Check insertion details
        assert editor.insertions[0].line == 1
        assert editor.insertions[0].insert_content == "# Enhanced Test Document"
        
        # Check deletion details
        assert editor.deletions[0].line == 1
        assert editor.deletions[0].existing_content == "# Test Document"
        assert "AI Edit" in editor.deletions[0].issue_message[0]
    
    @mock.patch('editai.editors.ai.get_line_edits')
    def test_collect_issues_with_delete(self, mock_get_line_edits, temp_markdown_file):
        """Test collect_issues with a delete resolution."""
        # Setup mock response
        mock_get_line_edits.return_value = LineEdits(
            line_edits=[
                LineEdit(
                    starting_affected_line=3,
                    ending_affected_line=3,
                    issue_message="Redundant text",
                    resolution="delete"
                )
            ]
        )
        
        editor = AIEditor(path=temp_markdown_file)
        editor.collect_issues()
        
        # Verify that only deletion was created
        assert len(editor.insertions) == 0
        assert len(editor.deletions) == 1
        
        # Check deletion details
        assert editor.deletions[0].line == 3
        assert editor.deletions[0].existing_content == "This is a test."
        assert "Redundant text" in editor.deletions[0].issue_message[0]
    
    @mock.patch('editai.editors.ai.get_line_edits')
    def test_collect_issues_with_flag(self, mock_get_line_edits, complex_markdown_file):
        """Test collect_issues with a flag resolution."""
        # Setup mock response
        mock_get_line_edits.return_value = LineEdits(
            line_edits=[
                LineEdit(
                    starting_affected_line=10,
                    ending_affected_line=12,
                    issue_message="Complex code block issue",
                    resolution="flag"
                )
            ]
        )
        
        editor = AIEditor(path=complex_markdown_file)
        editor.collect_issues()
        
        # Verify that no changes were made
        assert len(editor.insertions) == 0
        assert len(editor.deletions) == 0
    
    @mock.patch('editai.editors.ai.get_line_edits')
    @mock.patch('editai.editors.ai.fix_line_edit')
    def test_collect_issues_with_failed_edit(self, mock_fix_line_edit, mock_get_line_edits, 
                                             temp_markdown_file):
        """Test collect_issues when fix_line_edit returns None."""
        # Setup mock responses
        mock_get_line_edits.return_value = LineEdits(
            line_edits=[
                LineEdit(
                    starting_affected_line=1,
                    ending_affected_line=1,
                    issue_message="Title should be more descriptive",
                    resolution="edit"
                )
            ]
        )
        mock_fix_line_edit.return_value = None  # Simulate API failure
        
        editor = AIEditor(path=temp_markdown_file)
        editor.collect_issues()
        
        # Verify that no changes were made (should treat as flag)
        assert len(editor.insertions) == 0
        assert len(editor.deletions) == 0
    
    @mock.patch('editai.editors.ai.get_line_edits')
    @mock.patch('editai.editors.ai.fix_line_edit')
    def test_collect_issues_with_empty_edit(self, mock_fix_line_edit, mock_get_line_edits, 
                                            temp_markdown_file):
        """Test collect_issues when fix_line_edit returns empty string."""
        # Setup mock responses
        mock_get_line_edits.return_value = LineEdits(
            line_edits=[
                LineEdit(
                    starting_affected_line=1,
                    ending_affected_line=1,
                    issue_message="Title should be removed",
                    resolution="edit"
                )
            ]
        )
        mock_fix_line_edit.return_value = "   "  # Empty string with whitespace
        
        editor = AIEditor(path=temp_markdown_file)
        editor.collect_issues()
        
        # Verify that it was treated as delete
        assert len(editor.insertions) == 0
        assert len(editor.deletions) == 1
    
    @mock.patch('editai.editors.ai.get_line_edits')
    def test_collect_issues_with_invalid_line_numbers(self, mock_get_line_edits, temp_markdown_file):
        """Test collect_issues with invalid line numbers."""
        # Setup mock response with invalid line numbers
        mock_get_line_edits.return_value = LineEdits(
            line_edits=[
                LineEdit(
                    starting_affected_line=100,  # Invalid line number
                    ending_affected_line=101,
                    issue_message="This line doesn't exist",
                    resolution="edit"
                )
            ]
        )
        
        editor = AIEditor(path=temp_markdown_file)
        editor.collect_issues()
        
        # Verify that no changes were made
        assert len(editor.insertions) == 0
        assert len(editor.deletions) == 0
    
    @mock.patch('editai.editors.ai.get_line_edits')
    @mock.patch('editai.editors.ai.fix_line_edit')
    def test_collect_issues_with_overlapping_edits(self, mock_fix_line_edit, mock_get_line_edits, 
                                                  complex_markdown_file):
        """Test collect_issues with overlapping edits."""
        # Setup mock responses with overlapping line edits
        mock_get_line_edits.return_value = LineEdits(
            line_edits=[
                LineEdit(
                    starting_affected_line=1,
                    ending_affected_line=3,
                    issue_message="First edit",
                    resolution="edit"
                ),
                LineEdit(
                    starting_affected_line=2,  # Overlaps with first edit
                    ending_affected_line=4,
                    issue_message="Second edit",
                    resolution="edit"
                )
            ]
        )
        mock_fix_line_edit.return_value = "Modified content"
        
        editor = AIEditor(path=complex_markdown_file)
        editor.collect_issues()
        
        # Verify that only the first edit was applied
        assert len(editor.insertions) > 0
        assert len(editor.deletions) > 0
        
        # Check that only a single set of changes were made
        # This counts the number of unique lines affected by deletions
        affected_lines = set(issue.line for issue in editor.deletions)
        assert len(affected_lines) == 3  # Only lines 1-3 should be affected
    
    @mock.patch('editai.editors.ai.get_line_edits')
    @mock.patch('editai.editors.ai.fix_line_edit')
    def test_generate_v2(self, mock_fix_line_edit, mock_get_line_edits, temp_markdown_file):
        """Test generate_v2 integrates collect_issues and applies changes."""
        # Setup mock responses
        mock_get_line_edits.return_value = LineEdits(
            line_edits=[
                LineEdit(
                    starting_affected_line=1,
                    ending_affected_line=1,
                    issue_message="Title should be more descriptive",
                    resolution="edit"
                )
            ]
        )
        mock_fix_line_edit.return_value = "# Enhanced Test Document"
        
        editor = AIEditor(path=temp_markdown_file)
        result = editor.generate_v2()
        
        # Check the result content
        assert "# Enhanced Test Document" in result
        assert "# Test Document" not in result
        assert "This is a test." in result
    
    @mock.patch('editai.editors.ai.get_line_edits')
    def test_generate_v2_with_no_issues(self, mock_get_line_edits, temp_markdown_file):
        """Test generate_v2 when no issues are found."""
        # Setup mock response with no issues
        mock_get_line_edits.return_value = LineEdits(line_edits=[])
        
        editor = AIEditor(path=temp_markdown_file)
        result = editor.generate_v2()
        
        # Result should be unchanged
        assert result == "# Test Document\n\nThis is a test."