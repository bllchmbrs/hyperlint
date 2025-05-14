import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest import mock

from editai.cli import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestCLI:
    """Tests for the CLI commands."""
    
    @mock.patch('editai.cli.ValeEditor')
    @mock.patch('editai.cli.get_vale_config_path')
    def test_vale_single_file(self, mock_get_vale_config_path, mock_vale_editor, runner, tmp_path):
        """Test the vale command with a single file."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")

        # Mock the Vale config path
        mock_vale_config_path = tmp_path / ".vale.ini"
        mock_get_vale_config_path.return_value = mock_vale_config_path

        # Mock the editor
        mock_instance = mock_vale_editor.return_value
        mock_instance.generate_v2.return_value = "# Test Document (Fixed)"

        # Run the command
        result = runner.invoke(app, ['vale', str(test_file)])

        # Check the result
        assert result.exit_code == 0
        assert "Processed file" in result.stdout

        # Verify the editor was called correctly
        mock_vale_editor.assert_called_once()
        mock_instance.generate_v2.assert_called_once()
    
    @mock.patch('editai.cli.ValeEditor')
    @mock.patch('editai.cli.FolderProcessor')
    @mock.patch('editai.cli.get_vale_config_path')
    def test_vale_directory(self, mock_get_vale_config_path, mock_folder_processor, mock_vale_editor, runner, tmp_path):
        """Test the vale command with a directory."""
        # Create a test directory
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Mock the Vale config path
        mock_vale_config_path = tmp_path / ".vale.ini"
        mock_get_vale_config_path.return_value = mock_vale_config_path

        # Mock the folder processor
        mock_processor_instance = mock_folder_processor.return_value
        mock_processor_instance.process_directory.return_value = {
            "file1.md": "content1",
            "file2.md": "content2"
        }

        # Run the command
        result = runner.invoke(app, ['vale', str(test_dir)])

        # Check the result
        assert result.exit_code == 0
        assert "Processed 2 files" in result.stdout

        # Verify the folder processor was called correctly
        mock_folder_processor.assert_called_once()
        mock_processor_instance.process_directory.assert_called_once_with(dry_run=False)
    
    @mock.patch('editai.cli.ValeEditor')
    @mock.patch('editai.cli.get_vale_config_path')
    def test_vale_dry_run(self, mock_get_vale_config_path, mock_vale_editor, runner, tmp_path):
        """Test the vale command with dry run option."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")

        # Mock the Vale config path
        mock_vale_config_path = tmp_path / ".vale.ini"
        mock_get_vale_config_path.return_value = mock_vale_config_path

        # Mock the editor
        mock_instance = mock_vale_editor.return_value
        mock_instance.generate_v2.return_value = "# Test Document (Fixed)"

        # Run the command with dry run
        result = runner.invoke(app, ['vale', str(test_file), '--dry-run'])

        # Check the result
        assert result.exit_code == 0
        assert "Dry run - would update" in result.stdout
        assert "# Test Document (Fixed)" in result.stdout
    
    @mock.patch('editai.cli.AIEditor')
    def test_ai_single_file(self, mock_ai_editor, runner, tmp_path):
        """Test the ai command with a single file."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")
        
        # Mock the editor
        mock_instance = mock_ai_editor.return_value
        mock_instance.generate_v2.return_value = "# Test Document (Enhanced)"
        
        # Run the command
        result = runner.invoke(app, ['ai', str(test_file)])
        
        # Check the result
        assert result.exit_code == 0
        assert "Processed file" in result.stdout
        
        # Verify the editor was called correctly
        mock_ai_editor.assert_called_once()
        mock_instance.generate_v2.assert_called_once()
    
    @mock.patch('editai.cli.AIEditor')
    @mock.patch('editai.cli.FolderProcessor')
    def test_ai_directory(self, mock_folder_processor, mock_ai_editor, runner, tmp_path):
        """Test the ai command with a directory."""
        # Create a test directory
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Mock the folder processor
        mock_processor_instance = mock_folder_processor.return_value
        mock_processor_instance.process_directory.return_value = {
            "file1.md": "content1",
            "file2.md": "content2",
            "file3.md": "content3"
        }
        
        # Run the command
        result = runner.invoke(app, ['ai', str(test_dir), '--recursive'])
        
        # Check the result
        assert result.exit_code == 0
        assert "Processed 3 files" in result.stdout
        
        # Verify the folder processor was called correctly
        mock_folder_processor.assert_called_once_with(
            directory_path=Path(str(test_dir)), 
            editor_class=mock_ai_editor,
            editor_kwargs={},
            include_pattern="*.md",
            exclude_patterns=[],
            recursive=True
        )
    
    @mock.patch('editai.cli.CustomRuleEditor')
    def test_custom_rules_single_file(self, mock_custom_rule_editor, runner, tmp_path):
        """Test the custom-rules command with a single file."""
        # Create a test file and rules directory
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")
        
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "rule1.md").write_text("# Rule 1")
        
        # Mock the editor
        mock_instance = mock_custom_rule_editor.return_value
        mock_instance.generate_v2.return_value = "# Test Document (With Rules Applied)"
        
        # Run the command
        result = runner.invoke(app, [
            'custom-rules', 
            str(test_file), 
            str(rules_dir), 
            '--include-rules', 'rule1'
        ])
        
        # Check the result
        assert result.exit_code == 0
        assert "Processed file" in result.stdout
        
        # Verify the editor was called correctly
        mock_custom_rule_editor.assert_called_once_with(
            path=Path(str(test_file)),
            rules_directory=Path(str(rules_dir)),
            include_rules=['rule1'],
            exclude_rules=[],
            dry_run=False
        )
        mock_instance.generate_v2.assert_called_once()
    
    def test_list_rules(self, runner, tmp_path):
        """Test the list-rules command."""
        # Create a test rules directory with some rule files
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "rule1.md").write_text("# Rule 1")
        (rules_dir / "rule2.md").write_text("# Rule 2")
        (rules_dir / "rule3.md").write_text("# Rule 3")
        
        # Run the command
        result = runner.invoke(app, ['list-rules', str(rules_dir)])
        
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
        result = runner.invoke(app, ['view-rule', str(rules_dir), 'test_rule'])
        
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
        result = runner.invoke(app, ['create-rule', str(rules_dir), 'new_rule'])
        
        # Check the result
        assert result.exit_code == 0
        assert "Created rule" in result.stdout
        
        # Verify the file was created
        new_rule_path = rules_dir / "new_rule.md"
        assert new_rule_path.exists()
        assert "Rule: new_rule" in new_rule_path.read_text()
    
    @mock.patch('editai.cli.ArbitraryLinkEditor')
    def test_arbitrary_links(self, mock_arbitrary_link_editor, runner, tmp_path):
        """Test the arbitrary-links command."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")
        
        # Mock the editor
        mock_instance = mock_arbitrary_link_editor.return_value
        mock_instance.generate_v2.return_value = "# Test Document with Links"
        
        # Run the command
        result = runner.invoke(app, ['arbitrary-links', str(test_file)])
        
        # Check the result
        assert result.exit_code == 0
        assert "# Test Document with Links" in result.stdout
        
        # Verify the editor was called correctly
        mock_arbitrary_link_editor.assert_called_once_with(path=Path(str(test_file)))
        mock_instance.generate_v2.assert_called_once()
    
    def test_arbitrary_links_directory_error(self, runner, tmp_path):
        """Test the arbitrary-links command with directory path."""
        # Create a test directory
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        # Run the command with a directory path
        result = runner.invoke(app, ['arbitrary-links', str(test_dir)])
        
        # Check that it fails appropriately
        assert result.exit_code == 1
        assert "doesn't support directory processing" in result.stdout
    
    @mock.patch('editai.cli.InternalLinkEditor')
    def test_links_with_indexes(self, mock_internal_link_editor, runner, tmp_path):
        """Test the links command with index names."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")
        
        # Mock the editor
        mock_instance = mock_internal_link_editor.return_value
        mock_instance.generate_v2.return_value = "# Test Document with Internal Links"
        
        # Run the command with index names
        result = runner.invoke(app, [
            'links', 
            str(test_file), 
            '--local-index-names', 'index1,index2'
        ])
        
        # Check the result
        assert result.exit_code == 0
        assert "Processed file" in result.stdout
        
        # Verify the editor was called correctly
        mock_internal_link_editor.assert_called_once_with(
            path=Path(str(test_file)),
            indexes=['index1', 'index2']
        )
        mock_instance.generate_v2.assert_called_once()
    
    @mock.patch('editai.cli.ImageAdditionEditor')
    def test_add_images(self, mock_image_editor, runner, tmp_path):
        """Test the add-images command."""
        # Create a test file and image directory
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document")
        
        image_dir = tmp_path / "images"
        image_dir.mkdir()
        
        # Mock the editor
        mock_instance = mock_image_editor.return_value
        mock_instance.generate_v2.return_value = "# Test Document with Images"
        
        # Run the command
        result = runner.invoke(app, [
            'add-images', 
            str(test_file), 
            str(image_dir), 
            '--image-url-prefix', '/custom/images'
        ])
        
        # Check the result
        assert result.exit_code == 0
        assert "Processed file" in result.stdout
        
        # Verify the editor was called correctly
        mock_image_editor.assert_called_once_with(
            path=Path(str(test_file)),
            image_folder_path=Path(str(image_dir)),
            image_url_prefix='/custom/images',
            caption_model='claude-3-haiku-20240307',
            name_model='claude-3-haiku-20240307',
            location_model='claude-3-opus-20240229',
            amble_model='claude-3-haiku-20240307'
        )
        mock_instance.generate_v2.assert_called_once()