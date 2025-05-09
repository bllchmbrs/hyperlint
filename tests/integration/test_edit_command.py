import os
import tempfile
from pathlib import Path
import pytest
from typer.testing import CliRunner
from editai.cli import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_config_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
ai:
  model: "test-model"
  temperature: 0.5
vale:
  config_path: "./test-vale.ini"
custom_rules:
  rules_directory: "./rules"
  enabled_rules:
    - "test_rule"
recursive: true
dry_run: true  # Always use dry run for tests
include_pattern: "*.md"
        """)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_markdown_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Test Document

This is a test document for EditAI.

## Section 1

Some content here.

## Section 2

More content here.
""")
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_edit_command_help(runner):
    """Test the help output for the edit command."""
    result = runner.invoke(app, ["edit", "--help"])
    assert result.exit_code == 0
    assert "Run all configured editors on files" in result.stdout
    assert "--editors" in result.stdout
    assert "--exclude" in result.stdout
    assert "--parallel" in result.stdout
    assert "--sequential" in result.stdout


def test_edit_command_with_config(runner, temp_config_file, temp_markdown_file, monkeypatch):
    """Test the edit command with a configuration file."""
    # Mock the editor functions to avoid actual processing
    import editai.cli
    
    # Track editor calls
    editor_calls = []
    
    def mock_run_single_editor(editor_name, path, config, merged_config):
        editor_calls.append(editor_name)
        return {"file": str(path), "modified": False}
    
    monkeypatch.setattr(editai.cli, "run_single_editor", mock_run_single_editor)
    
    # Run the edit command with specific editors
    result = runner.invoke(
        app, 
        ["edit", str(temp_markdown_file), "--config", str(temp_config_file), "--editors", "ai,vale"]
    )
    
    # Check the command execution
    assert result.exit_code == 0
    assert "EditAI Summary" in result.stdout
    assert "AI Editor" in result.stdout
    assert "VALE Editor" in result.stdout
    
    # Check that only the specified editors were called
    assert len(editor_calls) == 2
    assert "ai" in editor_calls
    assert "vale" in editor_calls
    assert "custom_rules" not in editor_calls


def test_edit_command_exclude_editors(runner, temp_config_file, temp_markdown_file, monkeypatch):
    """Test the edit command with excluded editors."""
    # Mock the editor functions to avoid actual processing
    import editai.cli
    
    # Track editor calls
    editor_calls = []
    
    def mock_run_single_editor(editor_name, path, config, merged_config):
        editor_calls.append(editor_name)
        return {"file": str(path), "modified": False}
    
    monkeypatch.setattr(editai.cli, "run_single_editor", mock_run_single_editor)
    
    # Run the edit command with excluded editors
    result = runner.invoke(
        app, 
        ["edit", str(temp_markdown_file), "--config", str(temp_config_file), "--exclude", "vale,images"]
    )
    
    # Check the command execution
    assert result.exit_code == 0
    
    # Check that the specified editors were excluded
    assert "ai" in editor_calls
    assert "custom_rules" in editor_calls
    assert "links" in editor_calls
    assert "vale" not in editor_calls
    assert "images" not in editor_calls


def test_edit_command_sequential(runner, temp_config_file, temp_markdown_file, monkeypatch):
    """Test the edit command with sequential processing."""
    # Mock the editor functions to avoid actual processing
    import editai.cli
    
    sequential_called = False
    parallel_called = False
    
    def mock_run_sequential(*args, **kwargs):
        nonlocal sequential_called
        sequential_called = True
        return {"ai": {"file": str(temp_markdown_file), "modified": False}}
    
    def mock_run_parallel(*args, **kwargs):
        nonlocal parallel_called
        parallel_called = True
        return {"ai": {"file": str(temp_markdown_file), "modified": False}}
    
    monkeypatch.setattr(editai.cli, "run_editors_sequential", mock_run_sequential)
    monkeypatch.setattr(editai.cli, "run_editors_parallel", mock_run_parallel)
    
    # Run the edit command in sequential mode
    result = runner.invoke(
        app, 
        ["edit", str(temp_markdown_file), "--config", str(temp_config_file), "--sequential"]
    )
    
    # Check that sequential was called but parallel wasn't
    assert result.exit_code == 0
    assert sequential_called is True
    assert parallel_called is False


def test_edit_command_parallel(runner, temp_config_file, temp_markdown_file, monkeypatch):
    """Test the edit command with parallel processing."""
    # Mock the editor functions to avoid actual processing
    import editai.cli
    
    sequential_called = False
    parallel_called = False
    
    def mock_run_sequential(*args, **kwargs):
        nonlocal sequential_called
        sequential_called = True
        return {"ai": {"file": str(temp_markdown_file), "modified": False}}
    
    def mock_run_parallel(*args, **kwargs):
        nonlocal parallel_called
        parallel_called = True
        return {"ai": {"file": str(temp_markdown_file), "modified": False}}
    
    monkeypatch.setattr(editai.cli, "run_editors_sequential", mock_run_sequential)
    monkeypatch.setattr(editai.cli, "run_editors_parallel", mock_run_parallel)
    
    # Run the edit command in parallel mode (default)
    result = runner.invoke(
        app, 
        ["edit", str(temp_markdown_file), "--config", str(temp_config_file)]
    )
    
    # Check that parallel was called but sequential wasn't
    assert result.exit_code == 0
    assert sequential_called is False
    assert parallel_called is True