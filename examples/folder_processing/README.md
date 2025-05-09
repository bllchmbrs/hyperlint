# Folder Processing Example

This directory contains example files for testing the folder processing functionality.

## Contents

- `doc1.md` - Example document with passive voice and bullet point inconsistencies
- `doc2.md` - Second example document with more passive voice and bullet point inconsistencies
- `subfolder/doc3.md` - Nested example document to test recursive processing

## Testing Commands

You can test folder processing with the following commands:

### Process all files recursively

```bash
python -m tutedit.cli custom-rules ./examples/folder_processing/ ./test_rules/ --recursive --dry-run
```

### Process only top-level files

```bash
python -m tutedit.cli custom-rules ./examples/folder_processing/ ./test_rules/ --dry-run
```

### Process specific files by pattern

```bash
python -m tutedit.cli custom-rules ./examples/folder_processing/ ./test_rules/ --include-pattern "doc1*.md" --dry-run
```

### Exclude subfolder

```bash
python -m tutedit.cli custom-rules ./examples/folder_processing/ ./test_rules/ --exclude-patterns "subfolder/*" --recursive --dry-run
```

### Apply only specific rules

```bash
python -m tutedit.cli custom-rules ./examples/folder_processing/ ./test_rules/ --include-rules passive_voice --recursive --dry-run
```

## Expected Results

When applying the custom rules to these files, you should see:

1. Passive voice sentences converted to active voice
2. Bullet points consistently formatted (capitalized and with appropriate punctuation)

Remove the `--dry-run` flag to actually apply the changes to the files.