# EditAI Configuration System

EditAI provides a flexible configuration system that allows you to customize the behavior of all editors through a single YAML configuration file.

## Configuration File Locations

The system will look for configuration files in the following locations (in order):

1. The path specified with the `--config` option
2. `./editai.yaml` in the current working directory
3. `./.editai.yaml` in the current working directory
4. `~/.config/editai/config.yaml` in the user's home directory

## Creating a Configuration File

You can easily create a default configuration file using the `config init` command:

```bash
editai config init
```

This will create a file named `editai.yaml` in the current directory. You can specify a different path with the `--path` option:

```bash
editai config init --path ~/custom-editai-config.yaml
```

## Configuration Structure

The configuration file uses a simple, flat YAML structure:

```yaml
# Editor-specific configurations
ai:
  model: "openai/o3-mini-2025-01-31"
  fallback_model: "anthropic/claude-3-haiku-20240307"
  temperature: 0.25
  max_tokens: 2048
  cache_enabled: true
  
vale:
  config_path: "./.vale.ini"
  
custom_rules:
  rules_directory: "./rules"
  enabled_rules:
    - "passive_voice"
    - "bullet_consistency"
  disabled_rules:
    - "deprecated_terms"
    
images:
  default_url_prefix: "/images"
  caption_generation:
    enabled: true
    model: "claude-3-haiku-20240307"
    
links:
  default_indices:
    - "docs-index"
  auto_create_indices: true

# Global settings
recursive: true
dry_run: false
include_pattern: "*.md"
exclude_patterns: []
```

## The New `edit` Command

The new `edit` command allows you to run multiple editors in a single operation, either in parallel or sequentially:

```bash
editai edit ./docs/ --editors ai,vale --dry-run
```

### Command Options

- `--config, -c`: Path to a specific configuration file
- `--editors`: Comma-separated list of editors to run (default: all)
- `--exclude`: Comma-separated list of editors to exclude
- `--recursive/--no-recursive`: Whether to process subdirectories
- `--dry-run/--no-dry-run`: Preview changes without modifying files
- `--parallel/--sequential`: Run editors in parallel or one after another
- `--include`: File pattern to include (e.g., "*.md")
- `--exclude-patterns`: Patterns to exclude (e.g., "drafts/*.md,temp/*")

CLI options override the settings in the configuration file.

## Configuration Management Commands

EditAI provides several commands for managing configurations:

### Initialize a Configuration

```bash
editai config init
```

### View Current Configuration

```bash
editai config show
```

### Validate Configuration

```bash
editai config validate
```

## Editor-Specific Configuration

Each editor has its own section in the configuration file:

### AI Editor

```yaml
ai:
  model: "openai/o3-mini-2025-01-31"  # Primary LLM to use
  fallback_model: "anthropic/claude-3-haiku-20240307"  # Fallback model if primary fails
  temperature: 0.25  # Response randomness (0-1)
  max_tokens: 2048  # Maximum output tokens
  cache_enabled: true  # Whether to cache responses
```

### Vale Editor

```yaml
vale:
  config_path: "./.vale.ini"  # Path to Vale configuration
```

### Custom Rules Editor

```yaml
custom_rules:
  rules_directory: "./rules"  # Directory containing rule files
  enabled_rules:  # Rules to include (by filename without .md)
    - "passive_voice"
    - "bullet_consistency"
  disabled_rules:  # Rules to exclude
    - "deprecated_terms"
```

### Image Addition Editor

```yaml
images:
  default_url_prefix: "/images"  # Prefix for image URLs
  supported_formats: [".png", ".jpg", ".jpeg", ".gif"]  # Supported image formats
  caption_generation:  # Auto-generate captions for images
    enabled: true
    model: "claude-3-haiku-20240307"
```

### Link Editor

```yaml
links:
  default_indices:  # Default search indices
    - "docs-index"
    - "api-reference"
  auto_create_indices: true  # Create indices if they don't exist
```

## Global Settings

These settings apply to all editors:

```yaml
recursive: true  # Process subdirectories
dry_run: false  # Preview without making changes
include_pattern: "*.md"  # File pattern to include
exclude_patterns: []  # Patterns to exclude
```