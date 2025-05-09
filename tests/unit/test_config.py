import os
from pathlib import Path
import tempfile
import pytest
from editai.config import SimpleConfig, find_config_file, create_default_config


def test_simple_config_defaults():
    """Test that SimpleConfig initializes with correct defaults."""
    config = SimpleConfig()
    
    # Test default values
    assert config.ai == {}
    assert config.vale == {}
    assert config.custom_rules == {}
    assert config.images == {}
    assert config.links == {}
    assert config.recursive is True
    assert config.dry_run is False
    assert config.include_pattern == "*.md"
    assert config.exclude_patterns == []


def test_simple_config_from_yaml():
    """Test loading config from a YAML file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
ai:
  model: "test-model"
  temperature: 0.5
vale:
  config_path: "./test-vale.ini"
recursive: false
include_pattern: "**/*.md"
exclude_patterns:
  - "drafts/*.md"
  - "temp/*.md"
        """)
        temp_path = Path(f.name)
    
    try:
        config = SimpleConfig.from_yaml(temp_path)
        
        # Test values loaded from file
        assert config.ai == {"model": "test-model", "temperature": 0.5}
        assert config.vale == {"config_path": "./test-vale.ini"}
        assert config.custom_rules == {}  # Default
        assert config.recursive is False
        assert config.include_pattern == "**/*.md"
        assert config.exclude_patterns == ["drafts/*.md", "temp/*.md"]
    finally:
        temp_path.unlink()


def test_simple_config_from_yaml_invalid_file():
    """Test that loading from a non-existent file returns default config."""
    non_existent_path = Path("/non/existent/path.yaml")
    config = SimpleConfig.from_yaml(non_existent_path)
    
    # Should return default config
    assert config.ai == {}
    assert config.recursive is True
    assert config.include_pattern == "*.md"


def test_simple_config_from_yaml_invalid_yaml():
    """Test that loading invalid YAML returns default config."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
ai:
  model: "test-model"
  temperature: 0.5
invalid yaml structure
        """)
        temp_path = Path(f.name)
    
    try:
        config = SimpleConfig.from_yaml(temp_path)
        
        # Should return default config
        assert config.ai == {}
        assert config.recursive is True
    finally:
        temp_path.unlink()


def test_get_editor_config():
    """Test retrieving editor-specific config."""
    config = SimpleConfig()
    config.ai = {"model": "test-model", "temperature": 0.5}
    
    # Get existing editor config
    ai_config = config.get_editor_config("ai")
    assert ai_config == {"model": "test-model", "temperature": 0.5}
    
    # Get non-existent editor config
    unknown_config = config.get_editor_config("unknown")
    assert unknown_config == {}


def test_merge_with_cli():
    """Test merging CLI args with config."""
    config = SimpleConfig()
    config.ai = {"model": "default-model", "temperature": 0.5}
    config.recursive = True
    config.include_pattern = "*.md"
    
    # CLI args with some non-None values
    cli_args = {
        "recursive": False,  # Override
        "dry_run": True,    # Override
        "include_pattern": None,  # Don't override
        "exclude_patterns": ["temp/*"]  # Override
    }
    
    merged = config.merge_with_cli(cli_args)
    
    # Test merged values
    assert merged["recursive"] is False  # Overridden
    assert merged["dry_run"] is True     # Overridden
    assert merged["include_pattern"] == "*.md"  # Not overridden
    assert merged["exclude_patterns"] == ["temp/*"]  # Overridden
    assert merged["ai"] == {"model": "default-model", "temperature": 0.5}  # Not in CLI args


def test_find_config_file(monkeypatch):
    """Test finding config files in standard locations."""
    # Create a temporary directory as the working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Mock the current working directory
        monkeypatch.chdir(temp_dir_path)

        # No config file exists yet
        assert find_config_file() is None

        # Create a config file
        config_path = temp_dir_path / "editai.yaml"
        with open(config_path, 'w') as f:
            f.write("# Test config")

        # Should find the config file
        found_path = find_config_file()
        assert found_path is not None
        assert found_path.name == "editai.yaml"
        assert found_path.exists()


def test_create_default_config():
    """Test creating a default configuration file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        config_path = temp_dir_path / "test-config.yaml"
        
        # Create the default config
        path = create_default_config(config_path)
        
        # Check the file was created
        assert path.exists()
        
        # Check the file has content
        with open(path, 'r') as f:
            content = f.read()
            assert "model:" in content
            assert "config_path:" in content
            assert "rules_directory:" in content