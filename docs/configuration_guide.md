# Configuration Guide

EditAI provides a flexible configuration system that allows you to customize all aspects of the tool's behavior through a single YAML file. This guide explains how to create, manage, and use configuration effectively.

## Configuration File Basics

### File Locations

EditAI looks for configuration files in these locations (in order):

1. The path specified with the `--config` option
2. `./editai.yaml` in the current working directory
3. `./.editai.yaml` in the current working directory
4. `~/.config/editai/config.yaml` in the user's home directory

### Creating a Configuration File

The simplest way to create a configuration file is to use the built-in command:

```bash
editai config init
```

This creates a file named `editai.yaml` in your current directory with default settings and helpful comments.

To create the file in a different location:

```bash
editai config init --path ~/projects/docs/editai.yaml
```

### Validating Configuration

To check if your configuration file is valid:

```bash
editai config validate
```

This validates the YAML syntax and configuration structure.

### Viewing Current Configuration

To see the current active configuration:

```bash
editai config show
```

## Configuration Structure

The configuration file uses a simple, flat YAML structure with sections for each editor and global settings:

```yaml
# Editor-specific configurations
ai:
  model: "openai/o3-mini-2025-01-31"
  # More AI editor settings...
  
vale:
  config_path: "./.vale.ini"
  # More Vale editor settings...
  
custom_rules:
  rules_directory: "./rules"
  # More custom rules settings...
  
# ... Other editors ...

# Global settings
recursive: true
dry_run: false
include_pattern: "*.md"
exclude_patterns: []
```

## Editor-Specific Configuration

### AI Editor

```yaml
ai:
  # Primary LLM model to use
  model: "openai/o3-mini-2025-01-31"
  
  # Fallback model if primary fails
  fallback_model: "anthropic/claude-3-haiku-20240307"
  
  # Response randomness (0-1)
  temperature: 0.25
  
  # Maximum output tokens
  max_tokens: 2048
  
  # Enable/disable response caching
  cache_enabled: true
```

### Vale Editor

```yaml
vale:
  # Path to Vale configuration file
  config_path: "./.vale.ini"
```

### Custom Rules Editor

```yaml
custom_rules:
  # Directory containing rule files
  rules_directory: "./rules"
  
  # Rules to include (by filename without .md)
  enabled_rules:
    - "passive_voice"
    - "bullet_consistency"
  
  # Rules to exclude
  disabled_rules:
    - "deprecated_terms"
```

### Image Addition Editor

```yaml
images:
  # Prefix for image URLs
  default_url_prefix: "/images"
  
  # Auto-generate captions for images
  caption_generation:
    enabled: true
    model: "claude-3-haiku-20240307"
```

### Link Editor

```yaml
links:
  # Default search indices
  default_indices:
    - "docs-index"
    - "api-reference"
  
  # Create indices if they don't exist
  auto_create_indices: true
```

## Global Settings

These settings apply to all editors:

```yaml
# Process subdirectories
recursive: true

# Preview without making changes
dry_run: false

# File pattern to include
include_pattern: "*.md"

# Patterns to exclude
exclude_patterns:
  - "drafts/*"
  - "temp/*"
```

## Using Configuration with Commands

### The `edit` Command

The main way to use your configuration is with the `edit` command:

```bash
editai edit docs/
```

This applies all configured editors to the specified files, using the settings from your configuration file.

### Overriding Configuration

You can override configuration settings with command-line options:

```bash
# Override the recursive setting
editai edit docs/ --no-recursive

# Override dry-run setting
editai edit docs/ --dry-run

# Override file patterns
editai edit docs/ --include "*.md" --exclude-patterns "drafts/*,temp/*"
```

### Selecting Editors

You can specify which editors to use:

```bash
# Use only specific editors
editai edit docs/ --editors ai,vale,links

# Use all editors except some
editai edit docs/ --exclude custom_rules,images
```

### Parallel vs Sequential Execution

By default, editors run in parallel. For sequential execution:

```bash
editai edit docs/ --sequential
```

## Configuration Strategies

### Per-Project Configuration

Keep an `editai.yaml` file in each project's root directory with settings specific to that project.

### User Configuration

Create a global configuration at `~/.config/editai/config.yaml` with your preferred defaults.

### Team Configuration

Share a standardized configuration file with your team to ensure consistent editing across projects.

## Configuration Examples

### Documentation Project

```yaml
# Documentation project configuration
ai:
  model: "anthropic/claude-3-haiku-20240307"
  temperature: 0.1
  
custom_rules:
  rules_directory: "./doc-rules"
  enabled_rules:
    - "passive_voice"
    - "bullet_consistency"
    - "terminology"
    
links:
  default_indices:
    - "docs-index"
    - "api-reference"

# Set conservative defaults to avoid unwanted changes
recursive: false
dry_run: true
include_pattern: "*.md"
exclude_patterns:
  - "drafts/*"
  - "archive/*"
```

### Technical Blog

```yaml
# Blog configuration
ai:
  model: "openai/o3-mini-2025-01-31"
  temperature: 0.25
  
vale:
  config_path: "./blog/.vale.ini"
  
images:
  default_url_prefix: "/blog/images"
  caption_generation:
    enabled: true
    
recursive: true
include_pattern: "posts/*.md"
```

### API Documentation

```yaml
# API docs configuration
custom_rules:
  rules_directory: "./api-rules"
  enabled_rules:
    - "api_formatting"
    - "code_examples"
    - "parameter_tables"
    
links:
  default_indices:
    - "api-reference"
    
recursive: true
include_pattern: "api/*.md"
```

## Configuration Tips

1. **Start simple** - Begin with the default configuration and customize as needed
2. **Use dry-run first** - Set `dry_run: true` until you're confident in your settings
3. **Version control** - Keep your configuration file in version control with your project
4. **Document your settings** - Add comments to explain non-obvious configuration choices
5. **Update regularly** - Review and update your configuration as your needs evolve
6. **Use per-directory configs** - For large projects, consider different configs for different sections
7. **Validate after changes** - Always run `editai config validate` after editing the config file

## Troubleshooting

### Configuration Not Found

If EditAI can't find your configuration:
- Check that the file exists in one of the expected locations
- Use the `--config` option to specify the exact path
- Run `editai config show` to see which configuration is being used

### Invalid Configuration

If your configuration is invalid:
- Run `editai config validate` to identify issues
- Check your YAML syntax (indentation, quotes, etc.)
- Ensure all values have the correct types (strings, booleans, lists)

### Settings Not Applied

If your settings don't seem to be applied:
- Check that you're not overriding them with command-line options
- Verify the configuration being used with `editai config show`
- Check for typos in your configuration keys