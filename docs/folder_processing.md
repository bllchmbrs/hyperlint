# Folder Processing in Tutedit

Tutedit now supports processing multiple files in a directory using a single command.

## Overview

The folder processing feature allows you to run any of the document editing tools on all markdown files in a directory, rather than processing them one at a time. This is useful for:

- Applying consistent style rules across a documentation set
- Adding internal links across multiple related documents
- Performing AI-based improvements on all documentation files
- Adding images to all documents in a folder

## Usage

Most commands now detect whether the `path` parameter is a file or a directory. If it's a directory, the command will process all markdown files within that directory.

### Example Commands

```bash
# Apply custom rules to all markdown files in a directory
tutedit custom-rules ./docs/ ./rules/ --recursive

# Use AI to improve all markdown files in a directory
tutedit ai ./docs/ --recursive --include-pattern "*.md" --exclude-patterns "_drafts/*.md"

# Add internal links to all markdown files in a directory
tutedit links ./docs/ --local-index-names docs-index --recursive

# Run Vale on all markdown files in a directory
tutedit vale ./docs/ --vale-config-path ./.vale.ini --recursive
```

## Common Parameters

The following parameters are supported by all commands that accept directory paths:

- `--recursive`: Process subdirectories recursively (default: False)
- `--include-pattern`: Glob pattern for files to include (default: "*.md")
- `--exclude-patterns`: List of glob patterns for files to exclude
- `--dry-run`: Don't modify files, just show what would be changed

## Command-Specific Notes

### Arbitrary Links Editor

The `arbitrary-links` command does not support directory processing since it's an interactive command that requires user input for each document.

### Custom Rules Editor

When using `custom-rules` on a directory, you can still use the `--include-rules` and `--exclude-rules` parameters to control which rules are applied. These parameters are separate from the `--include-pattern` and `--exclude-patterns` parameters that control which files are processed.

## Best Practices

1. **Always use `--dry-run` first**: Before applying changes to multiple files, use the `--dry-run` option to see what changes would be made.

2. **Use `--include-pattern` and `--exclude-patterns`**: Narrow down the files to be processed to avoid changing files you don't intend to modify.

3. **Start with non-recursive mode**: Until you're comfortable with the behavior, avoid using `--recursive` to limit the scope of changes.

4. **Consider processing time**: Some editors, particularly the AI editor, may take significant time to process large numbers of files.

## Examples

### Process all markdown files in a directory recursively

```bash
tutedit custom-rules ./docs/ ./rules/ --recursive --dry-run
```

### Process only files in a specific pattern

```bash
tutedit ai ./guides/ --include-pattern "getting-started*.md"
```

### Exclude certain files or directories

```bash
tutedit vale ./docs/ --exclude-patterns "_drafts/*.md,internal/*.md" --recursive
```

### Process a nested directory structure

```bash
tutedit links ./documentation/ --recursive --exclude-patterns "assets/*,images/*,_templates/*"
```