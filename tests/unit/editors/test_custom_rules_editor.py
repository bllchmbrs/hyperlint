import pytest
from pathlib import Path
from unittest import mock

from editai.editors.custom_rules import CustomRuleEditor

@pytest.fixture
def rules_directory(tmp_path):
    """Creates a temporary directory with test rule files."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    
    # Create test rules
    rule_files = {
        "test_rule.md": "# Test Rule\nReplace 'foo' with 'bar'",
        "passive_voice.md": "# Passive Voice Rule\nConvert passive voice to active voice.\nExample: 'The bug was fixed by the team' → 'The team fixed the bug'",
        "formatting.md": "# Formatting Rule\nEnsure all bullet points end with a period."
    }
    
    for filename, content in rule_files.items():
        rule_file = rules_dir / filename
        rule_file.write_text(content)
    
    yield rules_dir

@pytest.fixture
def sample_markdown_file(tmp_path):
    """Creates a sample markdown file with text for rule application."""
    test_file = tmp_path / "test.md"
    test_file.write_text("""# Test Document

This file contains foo which should be replaced.
The data was processed by the system.

## List of items
- First item
- Second item
- Third item without period
""")
    return test_file


class TestCustomRuleEditor:
    """Tests for the CustomRuleEditor class."""
    
    def test_prerun_checks_success(self, rules_directory, sample_markdown_file):
        """Test prerun_checks with valid directory and rules."""
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory
        )
        
        result = editor.prerun_checks()
        
        assert result is True
    
    def test_prerun_checks_nonexistent_directory(self, sample_markdown_file, tmp_path):
        """Test prerun_checks with nonexistent directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=nonexistent_dir
        )
        
        result = editor.prerun_checks()
        
        assert result is False
    
    def test_prerun_checks_empty_directory(self, sample_markdown_file, tmp_path):
        """Test prerun_checks with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=empty_dir
        )
        
        result = editor.prerun_checks()
        
        assert result is False
    
    def test_load_rules(self, rules_directory, sample_markdown_file):
        """Test _load_rules loads all rule files."""
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory
        )
        
        rules = editor._load_rules()
        
        assert len(rules) == 3
        assert "test_rule" in rules
        assert "passive_voice" in rules
        assert "formatting" in rules
        assert "Replace 'foo' with 'bar'" in rules["test_rule"]
        assert "Convert passive voice to active voice" in rules["passive_voice"]
    
    def test_filter_rules_with_include(self, rules_directory, sample_markdown_file):
        """Test _filter_rules with include rules list."""
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory,
            include_rules=["test_rule"]
        )
        
        rules = editor._load_rules()
        filtered = editor._filter_rules(rules)
        
        assert len(filtered) == 1
        assert "test_rule" in filtered
        assert "passive_voice" not in filtered
        assert "formatting" not in filtered
    
    def test_filter_rules_with_exclude(self, rules_directory, sample_markdown_file):
        """Test _filter_rules with exclude rules list."""
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory,
            exclude_rules=["passive_voice"]
        )
        
        rules = editor._load_rules()
        filtered = editor._filter_rules(rules)
        
        assert len(filtered) == 2
        assert "test_rule" in filtered
        assert "passive_voice" not in filtered
        assert "formatting" in filtered
    
    def test_filter_rules_nonexistent_include(self, rules_directory, sample_markdown_file):
        """Test _filter_rules with nonexistent include rule."""
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory,
            include_rules=["nonexistent_rule"]
        )
        
        rules = editor._load_rules()
        filtered = editor._filter_rules(rules)
        
        assert len(filtered) == 0
    
    @mock.patch('editai.editors.custom_rules.fix_line_edit')
    def test_apply_rule(self, mock_fix_line_edit, rules_directory, sample_markdown_file):
        """Test apply_rule with a basic rule."""
        # Mock the fix_line_edit function to return a modified text
        mock_fix_line_edit.return_value = """# Test Document

This file contains bar which should be replaced.
The data was processed by the system.

## List of items
- First item
- Second item
- Third item without period
"""
        
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory
        )
        
        rule_content = "# Test Rule\nReplace 'foo' with 'bar'"
        editor.apply_rule(rule_content, "test_rule")
        
        # Check that fix_line_edit was called
        mock_fix_line_edit.assert_called_once()
        
        # Check that changes were recorded
        assert len(editor.deletions) > 0 or len(editor.insertions) > 0
        assert "test_rule" in editor.applied_rules
    
    @mock.patch('editai.editors.custom_rules.fix_line_edit')
    def test_apply_rule_dry_run(self, mock_fix_line_edit, rules_directory, sample_markdown_file):
        """Test apply_rule in dry run mode."""
        mock_fix_line_edit.return_value = """# Test Document

This file contains bar which should be replaced.
The data was processed by the system.

## List of items
- First item
- Second item
- Third item without period
"""
        
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory,
            dry_run=True
        )
        
        rule_content = "# Test Rule\nReplace 'foo' with 'bar'"
        editor.apply_rule(rule_content, "test_rule")
        
        # Check that fix_line_edit was called but no changes were recorded
        mock_fix_line_edit.assert_called_once()
        assert len(editor.deletions) == 0
        assert len(editor.insertions) == 0
        assert "test_rule" not in editor.applied_rules
    
    @mock.patch('editai.editors.custom_rules.fix_line_edit')
    def test_process_diff_with_same_line_count(self, mock_fix_line_edit, rules_directory, sample_markdown_file):
        """Test _process_diff with modified lines but same line count."""
        original_lines = ["Line 1", "Line 2", "Line 3"]
        corrected_lines = ["Line 1", "Modified Line 2", "Line 3"]
        
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory
        )
        
        editor._process_diff(original_lines, corrected_lines, "test_rule")
        
        # Should have one deletion and one insertion for the changed line
        assert len(editor.deletions) == 1
        assert len(editor.insertions) == 1
        assert editor.deletions[0].line == 2
        assert editor.deletions[0].existing_content == "Line 2"
        assert editor.insertions[0].line == 2
        assert editor.insertions[0].insert_content == "Modified Line 2"
    
    @mock.patch('editai.editors.custom_rules.fix_line_edit')
    def test_process_diff_with_different_line_count(self, mock_fix_line_edit, rules_directory, sample_markdown_file):
        """Test _process_diff with different line counts."""
        original_lines = ["Line 1", "Line 2", "Line 3"]
        corrected_lines = ["Line 1", "Modified Line 2", "Line 3", "New Line 4"]
        
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory
        )
        
        editor._process_diff(original_lines, corrected_lines, "test_rule")
        
        # Should delete all original lines and insert all new lines
        assert len(editor.deletions) == 3
        assert len(editor.insertions) == 4
        
        # Check deletion lines
        for i in range(3):
            assert editor.deletions[i].line == i + 1
            assert editor.deletions[i].existing_content == original_lines[i]
        
        # Check insertion lines
        for i in range(4):
            assert editor.insertions[i].line == i + 1
            assert editor.insertions[i].insert_content == corrected_lines[i]
    
    @mock.patch('editai.editors.custom_rules.fix_line_edit')
    def test_collect_issues(self, mock_fix_line_edit, rules_directory, sample_markdown_file):
        """Test collect_issues loads and applies rules."""
        # Mock the fix_line_edit function for each rule
        def side_effect(line_edit, content):
            # Simple replacement based on rule name
            if "test_rule" in str(line_edit.issue_message):
                return content.replace("foo", "bar")
            elif "passive_voice" in str(line_edit.issue_message):
                return content.replace("was processed by", "processed")
            elif "formatting" in str(line_edit.issue_message):
                return content.replace("Third item without period", "Third item without period.")
            return content
            
        mock_fix_line_edit.side_effect = side_effect
        
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory
        )
        
        editor.collect_issues()
        
        # Should have called fix_line_edit for each rule
        assert mock_fix_line_edit.call_count == 3
        
        # Check that all rules were applied
        assert len(editor.applied_rules) == 3
        assert set(editor.applied_rules) == {"test_rule", "passive_voice", "formatting"}
    
    @mock.patch('editai.editors.custom_rules.fix_line_edit')
    def test_generate_v2(self, mock_fix_line_edit, rules_directory, sample_markdown_file):
        """Test generate_v2 applies all rules and returns modified content."""
        # Read the original content
        with open(sample_markdown_file, "r") as f:
            original_content = f.read()
        
        # Mock the fix_line_edit function
        mock_fix_line_edit.return_value = """# Test Document

This file contains bar which should be replaced.
The system processed the data.

## List of items
- First item.
- Second item.
- Third item without period.
"""
        
        editor = CustomRuleEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory,
            include_rules=["test_rule"]  # Only use one rule for simplicity
        )
        
        result = editor.generate_v2()
        
        # Check that the content was modified
        assert result != original_content
        assert "bar" in result
        assert "foo" not in result