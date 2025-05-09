# EditAI

A Python tool for editing and improving Markdown documentation.

## Overview

EditAI provides various specialized editors for enhancing Markdown documentation:

- **Custom Rules Editor**: Apply user-defined editing rules from markdown files
- **Vale Editor**: Integrate with the Vale linting tool
- **AI Editor**: Use AI to identify and correct text issues
- **Internal Link Editor**: Add links between documents
- **Image Addition Editor**: Insert images into documents
- **Arbitrary Links Editor**: Interactive tool to add arbitrary links to a document

Each editor can process either single files or entire directories of markdown files.

With the new `edit` command, you can run multiple editors in a single operation, either in parallel or sequentially. The tool also supports a flexible YAML configuration system to customize all aspects of its behavior.

## Installation

```bash
# Install from source
pip install -e .
```

## Usage

### Custom Rules Editor

Apply custom plaintext markdown rules to your document:

```bash
# Process a single file
python -m editai.cli custom-rules my-document.md ./rules/

# Process a directory of files
python -m editai.cli custom-rules ./docs/ ./rules/ --recursive
```

### Vale Editor

Apply Vale linting rules to your document:

```bash
# Process a single file
python -m editai.cli vale my-document.md --vale-config-path ./.vale.ini

# Process a directory of files
python -m editai.cli vale ./docs/ --vale-config-path ./.vale.ini --recursive
```

### AI Editor

Use AI to improve your document:

```bash
# Process a single file
python -m editai.cli ai my-document.md

# Process a directory of files
python -m editai.cli ai ./docs/ --recursive
```

### Internal Link Editor

Add internal links to your document:

```bash
# Process a single file
python -m editai.cli links my-document.md --local-index-names docs-index

# Process a directory of files
python -m editai.cli links ./docs/ --local-index-names docs-index --recursive
```

See the [link editor guide](docs/link_editor_guide.md) for more information on setting up and using the link editor.

### Image Addition Editor

Add images to your document:

```bash
# Process a single file
python -m editai.cli add-images my-document.md ./images/ --image-url-prefix /images

# Process a directory of files
python -m editai.cli add-images ./docs/ ./images/ --image-url-prefix /images --recursive
```

### Arbitrary Links Editor

Interactive REPL to add arbitrary links to a document:

```bash
python -m editai.cli arbitrary-links my-document.md
```

Note: The arbitrary links editor does not support directory processing since it's interactive.

## Folder Processing

Process multiple files in a directory with a single command. Common options:

- `--recursive`: Process subdirectories recursively
- `--include-pattern`: Glob pattern for files to include (default: "*.md")
- `--exclude-patterns`: List of glob patterns for files to exclude
- `--dry-run`: Don't modify files, just show what would be changed

See the [folder processing documentation](docs/folder_processing.md) for more details.

## Custom Rules

Custom rules are plain markdown files containing editing instructions. Each rule file:

- Contains markdown instructions for a specific editing task
- Is processed by AI to interpret and apply changes
- Example rules: passive voice conversion, bullet point formatting

Managing rules:

```bash
# List all rules in a directory
python -m editai.cli list-rules ./rules/

# View a specific rule
python -m editai.cli view-rule ./rules/ passive_voice

# Create a new rule
python -m editai.cli create-rule ./rules/ my_new_rule
```

See the [custom rules guide](docs/custom_rules_guide.md) for detailed information on creating and using custom rules.

## Examples

Check the `examples/` directory for example files and usage scenarios.

## Configuration System

EditAI supports a flexible YAML configuration system:

```bash
# Create a default configuration file
python -m editai.cli config init

# Run the 'edit' command with all configured editors
python -m editai.cli edit ./docs/

# Run specific editors only
python -m editai.cli edit ./docs/ --editors ai,vale

# Exclude specific editors
python -m editai.cli edit ./docs/ --exclude custom_rules,images

# Run editors sequentially instead of in parallel
python -m editai.cli edit ./docs/ --sequential
```

See the [configuration documentation](docs/configuration.md) and the more comprehensive [configuration guide](docs/configuration_guide.md) for full details on the configuration system.

## Documentation

- [Command Reference](docs/command_reference.md) - Quick reference for all commands and options
- [Configuration Guide](docs/configuration_guide.md) - Detailed guide to configuration
- [Custom Rules Guide](docs/custom_rules_guide.md) - How to create and use custom rules
- [Link Editor Guide](docs/link_editor_guide.md) - Setting up and using the link editor
- [Folder Processing](docs/folder_processing.md) - Working with directories of files
- [Configuration Documentation](docs/configuration.md) - Basic configuration information
- [Troubleshooting](docs/troubleshooting.md) - Solving common issues

## License

MIT