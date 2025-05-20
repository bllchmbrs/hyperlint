from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from hyperlint.cli import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestCLI:
    """Tests for the CLI commands."""

    @mock.patch("hyperlint.cli.ValeEditor")
    def test_vale_single_file(self, mock_vale_editor, runner, tmp_path):
        """Test the vale command with a single file."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")

        # Mock the editor
        mock_instance = mock_vale_editor.return_value
        mock_instance.update_file.return_value = None

        # Run the command
        result = runner.invoke(app, ["apply", "vale", str(test_file)])

        # Check the result
        assert result.exit_code == 0

        # Verify the editor was called correctly
        mock_vale_editor.assert_called_once()
        mock_instance.update_file.assert_called_once()

    def test_vale_directory(self, runner, tmp_path):
        """Test the vale command with a directory - should fail."""
        # Create a test directory
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Run the command
        result = runner.invoke(app, ["apply", "vale", str(test_dir)])

        # Check that it fails appropriately
        assert result.exit_code == 1  # Path validation fails with code 1
        
    @mock.patch("hyperlint.cli.ValeEditor")
    def test_vale_dry_run(self, mock_vale_editor, runner, tmp_path):
        """Test the vale command with dry run option."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")

        # Mock the editor
        mock_instance = mock_vale_editor.return_value
        mock_instance.dry_run.return_value = None

        # Run the command with dry run
        result = runner.invoke(app, ["apply", "vale", str(test_file), "--dry-run"])

        # Check the result
        assert result.exit_code == 0

        # Verify dry run was called
        mock_instance.dry_run.assert_called_once()

    @mock.patch("hyperlint.cli.RulesEditor")
    def test_custom_rules_single_file(self, mock_rules_editor, runner, tmp_path):
        """Test the custom-rules command with a single file."""
        # Create a test file and rules directory
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")

        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "rule1.md").write_text("# Rule 1")

        # Mock the editor
        mock_instance = mock_rules_editor.return_value
        mock_instance.update_file.return_value = None

        # Run the command
        result = runner.invoke(
            app,
            [
                "apply",
                "rules",
                str(test_file),
                str(rules_dir),
                "--include-rules",
                "rule1",
            ],
        )

        # Check the result
        assert result.exit_code == 0

        # Verify the editor was called correctly
        mock_rules_editor.assert_called_once_with(
            path=Path(str(test_file)),
            rules_directory=Path(str(rules_dir)),
            include_rules=["rule1"],
            exclude_rules=[],
            dry_run=False,
        )
        mock_instance.update_file.assert_called_once()

    def test_list_rules(self, runner, tmp_path):
        """Test the list-rules command."""
        # Create a test rules directory with some rule files
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "rule1.md").write_text("# Rule 1")
        (rules_dir / "rule2.md").write_text("# Rule 2")
        (rules_dir / "rule3.md").write_text("# Rule 3")

        # Run the command
        result = runner.invoke(app, ["manage-rules", "list", str(rules_dir)])

        # Check the result
        assert result.exit_code == 0
        assert "Found 3 rules" in result.stdout
        assert "- rule1" in result.stdout
        assert "- rule2" in result.stdout
        assert "- rule3" in result.stdout

    def test_view_rule(self, runner, tmp_path):
        """Test the view-rule command."""
        # Create a test rules directory with a rule file
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "test_rule.md").write_text("# Test Rule\nThis is a test rule.")

        # Run the command
        result = runner.invoke(app, ["manage-rules", "view", str(rules_dir), "test_rule"])

        # Check the result
        assert result.exit_code == 0
        assert "--- Rule: test_rule ---" in result.stdout
        assert "This is a test rule." in result.stdout

    def test_create_rule(self, runner, tmp_path):
        """Test the create-rule command."""
        # Create a test rules directory
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()

        # Run the command
        result = runner.invoke(app, ["manage-rules", "create", str(rules_dir), "new_rule"])

        # Check the result
        assert result.exit_code == 0
        assert "Created rule" in result.stdout

        # Verify the file was created
        new_rule_path = rules_dir / "new_rule.md"
        assert new_rule_path.exists()
        assert "Rule: new_rule" in new_rule_path.read_text()