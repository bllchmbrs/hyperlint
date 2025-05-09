# EditAI Command Reference

This cheat sheet provides a quick reference for all EditAI commands and their common options.

## Core Commands

| Command | Description | Basic Usage |
|---------|-------------|-------------|
| `edit` | Run multiple editors on files | `editai edit docs/` |
| `ai` | Use AI to improve documents | `editai ai README.md` |
| `vale` | Run Vale style checks | `editai vale docs/guide.md` |
| `links` | Add internal links | `editai links docs/` |
| `add-images` | Add images to documents | `editai add-images docs/ images/` |
| `custom-rules` | Apply custom editing rules | `editai custom-rules docs/ rules/` |
| `arbitrary-links` | Interactive link addition | `editai arbitrary-links README.md` |

## Configuration Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `config init` | Create default config | `editai config init` |
| `config show` | Display current config | `editai config show` |
| `config validate` | Check config validity | `editai config validate` |

## Custom Rules Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `list-rules` | List available rules | `editai list-rules rules/` |
| `view-rule` | Display rule content | `editai view-rule rules/ rule_name` |
| `create-rule` | Create a new rule | `editai create-rule rules/ new_rule` |

## Common Options

These options work with most commands:

| Option | Description | Example |
|--------|-------------|---------|
| `--recursive` | Process subdirectories | `editai ai docs/ --recursive` |
| `--dry-run` | Preview without changes | `editai vale docs/ --dry-run` |
| `--include-pattern` | File pattern to include | `editai ai docs/ --include-pattern "*.md"` |
| `--exclude-patterns` | Patterns to exclude | `editai ai docs/ --exclude-patterns "drafts/*,temp/*"` |

## Editor-Specific Options

### vale

```bash
editai vale docs/guide.md --vale-config-path .vale.ini
```

### links

```bash
editai links docs/ --local-index-names docs-index,api-docs --websearch
```

### add-images

```bash
editai add-images docs/ images/ --image-url-prefix /assets/images
```

### custom-rules

```bash
editai custom-rules docs/ rules/ --include-rules passive_voice,formatting
editai custom-rules docs/ rules/ --exclude-rules deprecated_terms
```

## Edit Command Options

```bash
# Run specific editors
editai edit docs/ --editors ai,vale,links

# Exclude specific editors
editai edit docs/ --exclude custom_rules,images

# Use sequential execution
editai edit docs/ --sequential

# Use specific config
editai edit docs/ --config ./custom-config.yaml
```

## Common Workflows

### Initial Document Cleanup

```bash
# First apply AI improvements
editai ai docs/getting-started.md --dry-run

# Then apply specific custom rules
editai custom-rules docs/getting-started.md rules/ --include-rules passive_voice,formatting

# Finally add internal links
editai links docs/getting-started.md --local-index-names docs-index
```

### Batch Processing

```bash
# Process all documentation with all editors
editai edit docs/ --recursive
```

### Style Checking Only

```bash
# Check style without making changes
editai vale docs/ --dry-run --recursive
```

### Rule Development

```bash
# Create a new rule
editai create-rule rules/ my_new_rule

# Test the rule
editai custom-rules test_sample.md rules/ --include-rules my_new_rule --dry-run
```

### Configuration Setup

```bash
# Create default config
editai config init

# Validate after editing
editai config validate
```

## Tips

- Use `--dry-run` to preview changes before applying them
- Process directories recursively with `--recursive`
- Combine editors with the `edit` command for maximum efficiency
- For best performance, let editors run in parallel (default)
- Create and maintain a library of custom rules for consistent editing
- Create focused indices for the link editor to improve relevance