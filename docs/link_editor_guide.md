# Link Editor Guide

EditAI's link editor automates the process of adding internal links between your documentation files. This guide explains how to set up and use the link editor effectively.

## How the Link Editor Works

The link editor:
1. Analyzes your document to identify important terms and concepts
2. Searches specified indices for relevant content that matches these terms
3. Intelligently places markdown links in the document where they make the most sense
4. Preserves your document's flow and structure while adding helpful connections

## Setting Up Indices

The link editor relies on search indices to find relevant content. These indices are created and managed using `smolcrawl`, a lightweight indexing tool.

### Viewing Available Indices

To see what indices are already available:

```bash
editai list-indices
```

### Creating Indices

You'll need to use the `smolcrawl` tool directly to create indices:

```bash
# Install smolcrawl if you don't have it
pip install smolcrawl

# Create an index from a directory of markdown files
smolcrawl create-index docs-index ./docs/

# Create an index from a website
smolcrawl create-index api-docs https://api.example.com/docs/
```

### Best Practices for Indices

For the best results:
- Create separate indices for different document collections
- Name indices descriptively (e.g., `api-docs`, `user-guide`)
- Update indices when your documentation changes significantly
- Keep indices focused on related content

## Using the Link Editor

### Basic Usage

To add links to a single document using the default index:

```bash
editai links path/to/document.md
```

### Using Specific Indices

To use specific indices when adding links:

```bash
editai links path/to/document.md --local-index-names api-docs,user-guide
```

### Processing Multiple Files

To process an entire directory of files:

```bash
editai links docs/ --recursive
```

### Web Search Integration

The link editor can also search the web for relevant external resources:

```bash
editai links README.md --websearch
```

This option should be used sparingly as it may add links to external sites that could change or disappear.

### Preview Mode

To see what links would be added without actually changing files:

```bash
editai links docs/ --dry-run
```

## Configuration

You can configure default indices and behavior in your `editai.yaml` configuration file:

```yaml
links:
  default_indices:
    - "docs-index"
    - "api-reference"
  auto_create_indices: true
```

With this configuration, the `links` command will use both indices by default.

## Advanced Usage

### Combining with Other Editors

The link editor works well in combination with other editors. For example:

```bash
editai edit docs/ --editors ai,links
```

This applies both the AI editor and the link editor to your documents.

### Controlling Link Density

By default, the link editor adds links wherever they make sense, which could result in too many links in some cases. You can apply a custom rule afterward to limit link density:

```markdown
# Rule: link_density

Ensure each paragraph has at most 2 links. Remove any excess links,
prioritizing the most relevant ones. Avoid having links to the same
destination appearing multiple times in close proximity.
```

## Troubleshooting

### No Links Added

If no links are being added, check:
- The index exists and contains relevant content
- Your document contains terms that match indexed content
- You're using the correct index name

### Too Many Links

If too many links are being added:
- Create more focused indices
- Use a custom rule to reduce link density
- Apply the link editor more selectively to specific documents

### Index Not Found

If you get an "Index does not exist" error:
- Check that you've created the index with `smolcrawl`
- Verify the index name spelling
- If using `auto_create_indices: true`, check permissions

## Examples

### Example 1: API Documentation

```bash
# Create an index of your API reference
smolcrawl create-index api-docs ./api-reference/

# Add links to your getting-started guide
editai links ./docs/getting-started.md --local-index-names api-docs
```

### Example 2: Complete Documentation Set

```bash
# Create indices for different document types
smolcrawl create-index user-guide ./docs/user-guide/
smolcrawl create-index api-docs ./docs/api/
smolcrawl create-index tutorials ./docs/tutorials/

# Process all documentation with links
editai links ./docs/ --local-index-names user-guide,api-docs,tutorials --recursive
```

### Example 3: Configuration File Approach

Create a configuration file:

```yaml
# editai.yaml
links:
  default_indices:
    - "user-guide"
    - "api-docs"
    - "tutorials"
```

Then simply run:

```bash
editai edit ./docs/ --editors links --recursive
```

## Best Practices

1. **Create focused indices** - Separate indices by document type or audience
2. **Update indices regularly** - Rebuild when documentation changes significantly
3. **Use preview mode** - Always check changes with `--dry-run` first
4. **Be selective** - Not every document needs links added
5. **Consider context** - Links should enhance, not distract from, the content
6. **Review and edit** - AI-generated links may need human refinement
7. **Document your indices** - Keep a list of what each index contains