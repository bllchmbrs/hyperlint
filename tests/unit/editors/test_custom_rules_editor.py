from unittest import mock

import pytest

from hyperlint.editors.custom_rules import RulesEditor, RulesViolation


@pytest.fixture
def rules_directory(tmp_path):
    """Creates a temporary directory with test rule files."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Create test rules
    rule_files = {
        "test_rule.md": "# Test Rule\nReplace 'foo' with 'bar'",
        "passive_voice.md": "# Passive Voice Rule\nConvert passive voice to active voice.\nExample: 'The bug was fixed by the team' → 'The team fixed the bug'",
        "formatting.md": "# Formatting Rule\nEnsure all bullet points end with a period.",
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
    """Tests for the RulesEditor class."""

    def test_prerun_checks_success(self, rules_directory, sample_markdown_file):
        """Test prerun_checks with valid directory and rules."""
        editor = RulesEditor(path=sample_markdown_file, rules_directory=rules_directory)

        result = editor.prerun_checks()

        assert result is True

    def test_prerun_checks_nonexistent_directory(self, sample_markdown_file, tmp_path):
        """Test prerun_checks with nonexistent directory."""
        nonexistent_dir = tmp_path / "nonexistent"

        editor = RulesEditor(path=sample_markdown_file, rules_directory=nonexistent_dir)

        result = editor.prerun_checks()

        assert result is False

    def test_prerun_checks_empty_directory(self, sample_markdown_file, tmp_path):
        """Test prerun_checks with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        editor = RulesEditor(path=sample_markdown_file, rules_directory=empty_dir)

        result = editor.prerun_checks()

        assert result is False

    def test_load_rules(self, rules_directory, sample_markdown_file):
        """Test _load_rules loads all rule files."""
        editor = RulesEditor(path=sample_markdown_file, rules_directory=rules_directory)

        rules = editor._load_rules()

        assert len(rules) == 3
        assert "test_rule" in rules
        assert "passive_voice" in rules
        assert "formatting" in rules
        assert "Replace 'foo' with 'bar'" in rules["test_rule"]
        assert "Convert passive voice to active voice" in rules["passive_voice"]

    def test_filter_rules_with_include(self, rules_directory, sample_markdown_file):
        """Test _filter_rules with include rules list."""
        editor = RulesEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory,
            include_rules=["test_rule"],
        )

        rules = editor._load_rules()
        filtered = editor._filter_rules(rules)

        assert len(filtered) == 1
        assert "test_rule" in filtered
        assert "passive_voice" not in filtered
        assert "formatting" not in filtered

    def test_filter_rules_with_exclude(self, rules_directory, sample_markdown_file):
        """Test _filter_rules with exclude rules list."""
        editor = RulesEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory,
            exclude_rules=["passive_voice"],
        )

        rules = editor._load_rules()
        filtered = editor._filter_rules(rules)

        assert len(filtered) == 2
        assert "test_rule" in filtered
        assert "passive_voice" not in filtered
        assert "formatting" in filtered

    def test_filter_rules_nonexistent_include(
        self, rules_directory, sample_markdown_file
    ):
        """Test _filter_rules with nonexistent include rule."""
        editor = RulesEditor(
            path=sample_markdown_file,
            rules_directory=rules_directory,
            include_rules=["nonexistent_rule"],
        )

        rules = editor._load_rules()
        filtered = editor._filter_rules(rules)

        assert len(filtered) == 0

    @mock.patch("hyperlint.editors.custom_rules.get_issues")
    def test_apply_rule(self, mock_get_issues, rules_directory, sample_markdown_file):
        """Test apply_rule with a basic rule."""
        # Mock get_issues to return a violation
        mock_get_issues.return_value = [
            RulesViolation(
                line_number=3,
                issue_message="Replace 'foo' with 'bar'",
                resolution="edit_line",
            )
        ]

        editor = RulesEditor(path=sample_markdown_file, rules_directory=rules_directory)

        rule_content = "# Test Rule\nReplace 'foo' with 'bar'"
        editor.apply_rule(rule_content, "test_rule")

        # Check that get_issues was called
        mock_get_issues.assert_called_once()

        # Check that changes were recorded
        assert len(editor.replacements) == 1
        assert "test_rule" in editor.applied_rules

    @mock.patch("hyperlint.editors.custom_rules.get_issues")
    def test_apply_rule_dry_run(
        self, mock_get_issues, rules_directory, sample_markdown_file
    ):
        """Test apply_rule in dry run mode."""
        mock_get_issues.return_value = [
            RulesViolation(
                line_number=3,
                issue_message="Replace 'foo' with 'bar'",
                resolution="edit_line",
            )
        ]

        editor = RulesEditor(
            path=sample_markdown_file, rules_directory=rules_directory, dry_run=True
        )

        rule_content = "# Test Rule\nReplace 'foo' with 'bar'"
        editor.apply_rule(rule_content, "test_rule")

        # Check that get_issues was called but no changes were recorded
        mock_get_issues.assert_called_once()
        assert len(editor.replacements) == 0
        assert len(editor.deletions) == 0
        assert len(editor.insertions) == 0
        assert "test_rule" not in editor.applied_rules

    def test_line_lookup_and_numbering(self, rules_directory, sample_markdown_file):
        """Test get_line_number_lookup and get_text_with_line_numbers."""
        editor = RulesEditor(path=sample_markdown_file, rules_directory=rules_directory)

        # Test line number lookup
        line_lookup = editor.get_line_number_lookup()
        assert len(line_lookup) == 10
        assert line_lookup[1] == "# Test Document"
        assert line_lookup[3] == "This file contains foo which should be replaced."

        # Test text with line numbers
        numbered_text = editor.get_text_with_line_numbers()
        assert numbered_text.startswith("1: # Test Document")
        assert "3: This file contains foo which should be replaced." in numbered_text

    @mock.patch("hyperlint.editors.custom_rules.get_issues")
    def test_apply_rule_with_edit_lines(
        self, mock_get_issues, rules_directory, sample_markdown_file
    ):
        """Test apply_rule with edit_line resolution."""
        mock_get_issues.return_value = [
            RulesViolation(
                line_number=3,
                issue_message="Replace 'foo' with 'bar'",
                resolution="edit_line",
            )
        ]

        editor = RulesEditor(path=sample_markdown_file, rules_directory=rules_directory)
        editor.apply_rule("# Test Rule\nReplace foo with bar", "test_rule")

        assert len(editor.replacements) == 1
        assert editor.replacements[0].line == 3
        assert (
            editor.replacements[0].existing_content
            == "This file contains foo which should be replaced."
        )
        assert "test_rule" in editor.applied_rules

    @mock.patch("hyperlint.editors.custom_rules.get_issues")
    def test_collect_issues(
        self, mock_get_issues, rules_directory, sample_markdown_file
    ):
        """Test collect_issues loads and applies rules."""

        def mock_get_issues_side_effect(text, rule_content, rule_name):
            issues = []
            if rule_name == "test_rule":
                issues.append(
                    RulesViolation(
                        line_number=3,
                        issue_message="Replace 'foo' with 'bar'",
                        resolution="edit_line",
                    )
                )
            elif rule_name == "passive_voice":
                issues.append(
                    RulesViolation(
                        line_number=4,
                        issue_message="Fix passive voice",
                        resolution="edit_line",
                    )
                )
            elif rule_name == "formatting":
                issues.append(
                    RulesViolation(
                        line_number=8,
                        issue_message="Add period",
                        resolution="edit_line",
                    )
                )
            return issues

        mock_get_issues.side_effect = mock_get_issues_side_effect

        editor = RulesEditor(path=sample_markdown_file, rules_directory=rules_directory)
        editor.collect_issues()

        # Should have called get_issues for each rule
        assert mock_get_issues.call_count == 3

        # Check that all rules were applied
        assert len(editor.replacements) == 3
        assert len(editor.applied_rules) == 3
        assert set(editor.applied_rules) == {"test_rule", "passive_voice", "formatting"}

    @mock.patch("hyperlint.editors.custom_rules.get_issues")
    def test_apply_rule_with_multiple_resolutions(
        self, mock_get_issues, rules_directory, sample_markdown_file
    ):
        """Test apply_rule with multiple resolution types."""
        mock_get_issues.return_value = [
            RulesViolation(
                line_number=3,
                issue_message="Replace 'foo' with 'bar'",
                resolution="edit_line",
            ),
            RulesViolation(
                line_number=4,
                issue_message="Remove passive voice line",
                resolution="delete_line",
            ),
        ]

        editor = RulesEditor(path=sample_markdown_file, rules_directory=rules_directory)
        editor.apply_rule("# Test Rule\nMultiple fixes", "test_rule")

        # Check replacements
        assert len(editor.replacements) == 1
        assert editor.replacements[0].line == 3

        # Check deletions
        assert len(editor.deletions) == 1
        assert editor.deletions[0].line == 4

        # Check insertions
        assert len(editor.insertions) == 0

        assert "test_rule" in editor.applied_rules
