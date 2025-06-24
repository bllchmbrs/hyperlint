# Hyperlint

A Python CLI tool for editing and improving Markdown documentation using AI-powered rules and Vale linting.

## Features

- **AI-Powered Editing**: Apply custom rules using large language models to improve documentation
- **Vale Integration**: Lint markdown files using Vale style checking
- **Interactive Approval**: Review and approve changes before applying them
- **Batch Processing**: Process single files or entire directories
- **MDX Support**: Full support for `.md` and `.mdx` files
- **Flexible Configuration**: YAML-based configuration with multiple search paths

## Installation

```bash
# Install dependencies
uv sync --dev

# Run the CLI
uv run hyperlint --help
```

## Quick Start

```bash
# Apply rules to a single file
uv run hyperlint apply rules path/to/file.md

# Apply Vale linting to a directory
uv run hyperlint apply vale docs/ --recursive

# Initialize default configuration
uv run hyperlint config init

# Create custom rules
uv run hyperlint manage-rules create
```

## Commands

### Apply Commands

- `hyperlint apply rules <path>` - Apply AI-powered custom rules to markdown files
- `hyperlint apply vale <path>` - Apply Vale linting to markdown files

**Options:**
- `--recursive` - Process directories recursively
- `--include <pattern>` - Include files matching glob pattern
- `--exclude <pattern>` - Exclude files matching glob pattern
- `--approval-type <type>` - Set approval type (console, image, silent)
- `--dry-run` - Preview changes without applying them

### Configuration Commands

- `hyperlint config init` - Initialize default configuration files
- `hyperlint config show` - Show current configuration

### Rule Management Commands

- `hyperlint manage-rules create` - Create new custom rules
- `hyperlint manage-rules list` - List existing rules
- `hyperlint manage-rules edit <rule>` - Edit existing rules

## Configuration

Hyperlint uses YAML configuration files searched in the following order:
1. `.hyperlint.yaml` (current directory)
2. `hyperlint.yaml` (current directory)
3. `~/.config/hyperlint/config.yaml` (user config)

Example configuration:

```yaml
# Vale configuration
vale:
  config_path: ".vale.ini"
  styles_path: "styles/"

# Custom rules configuration
custom_rules:
  model: "gpt-4"
  temperature: 0.1
  rules_directory: "rules/"

# Storage configuration
storage:
  approval_log_dir: "logs/approvals/"
```

## Architecture

### Core Components

- **CLI Interface** (`cli.py`): Typer-based command interface with three main command groups
- **Editors** (`editors/`): Pluggable editor system for different types of checks
  - `vale.py`: Vale linter integration
  - `custom_rules.py`: AI-powered rule application
  - `core.py`: Abstract base classes and shared functionality
- **Configuration** (`config.py`): Pydantic-based configuration management
- **Approval System** (`approval.py`): Interactive workflow for reviewing changes

### Editor Pattern

All editors inherit from `BaseEditor` and implement:
- `get_issues()`: Detect problems in markdown
- `update_file()`: Apply fixes with approval workflow
- `dry_run()`: Preview changes without applying

## Development

### Setup

```bash
# Install dependencies
uv sync --dev

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format code
uv run ruff format src/
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_file.py::test_function

# Run test directory
uv run pytest tests/unit/
```

## Requirements

- Python >=3.11
- uv package manager

## Dependencies

- **CLI**: Typer, Rich
- **AI**: LiteLLM, Instructor, DSPy
- **Parsing**: SpaCy, custom MDX parser
- **Storage**: DiskCache, PyYAML
- **Linting**: Vale (external dependency)

## License

[Add your license information here]