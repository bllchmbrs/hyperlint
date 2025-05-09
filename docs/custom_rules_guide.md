# Custom Rules Guide

EditAI's custom rules feature allows you to create markdown-based editing rules that can be applied to your documentation. These rules act as instructions for AI-powered edits, making them highly flexible and powerful.

## What Are Custom Rules?

Custom rules are markdown files containing natural language instructions for editing text. Unlike traditional regex or pattern-based replacements, these rules leverage AI to understand the context and intent of your content, making more intelligent edits.

Each rule should focus on a specific type of edit, such as:
- Converting passive voice to active voice
- Standardizing bullet point formatting
- Replacing deprecated terminology
- Fixing common grammatical issues
- Standardizing headings
- Adding consistent document structures

## Creating a Custom Rule

To create a new rule:

```bash
editai create-rule rules/ my_rule_name
```

This creates a template rule file at `rules/my_rule_name.md`.

## Rule Structure

A custom rule file has a simple structure:

```markdown
# Rule: rule_name

Instructions for the rule go here. Describe the changes to make to the document.

Example:
- Find instances of passive voice and convert to active voice
- Ensure bullet points are consistently formatted
- Replace deprecated terminology with approved terms
```

### Writing Effective Instructions

For best results, your instructions should be:

1. **Clear and specific** - Describe exactly what changes should be made
2. **Contextual** - Explain when and how changes should be applied
3. **Example-driven** - Include examples of before/after transformations
4. **Focused** - Each rule should address one specific type of edit

## Example Rules

### Passive Voice Correction

```markdown
# Rule: passive_voice

Find instances of passive voice in the document and convert them to active voice.

For example:
- Passive: "The button is clicked by the user"
- Active: "The user clicks the button"

- Passive: "The data is processed by the system"
- Active: "The system processes the data"

Make sure to maintain the original meaning while making the text more direct.
Only change sentences that would benefit from active voice - some passive
constructions are appropriate when the actor is unknown or irrelevant.
```

### Bullet Point Consistency

```markdown
# Rule: bullet_consistency

Standardize all bullet points in the document to follow these rules:

1. Always use hyphens (-) for top-level bullets
2. Always use asterisks (*) for second-level bullets
3. Start each bullet with a capital letter
4. End each bullet with a period if it forms a complete sentence
5. Don't use periods for incomplete phrases or single words
6. Keep bullets parallel in structure (all sentences, all phrases, or all words)

For example:
Before:
• First item
* Second item.
+ Third item

After:
- First item
- Second item
- Third item

Before:
- installing the software
- RUN the program.
- Configuration IS IMPORTANT

After:
- Install the software
- Run the program
- Configure the settings
```

### Terminology Replacement

```markdown
# Rule: deprecated_terms

Replace deprecated or outdated terminology with the current preferred terms:

- Replace "whitelist" with "allowlist"
- Replace "blacklist" with "denylist" or "blocklist"
- Replace "master/slave" with "primary/replica" or "main/secondary"
- Replace "man hours" with "person hours" or "work hours"
- Replace "sanity check" with "basic check" or "initial verification"
- Replace "native feature" with "built-in feature"

Only replace these terms when they're used in a technical context, and make
sure to maintain grammar and sentence structure when making replacements.
```

## Applying Rules

Apply all rules in a directory:

```bash
editai custom-rules path/to/document.md rules/
```

Apply specific rules only:

```bash
editai custom-rules path/to/document.md rules/ --include-rules passive_voice,bullet_consistency
```

Exclude certain rules:

```bash
editai custom-rules path/to/document.md rules/ --exclude-rules deprecated_terms
```

Preview changes without applying them:

```bash
editai custom-rules path/to/document.md rules/ --dry-run
```

## Managing Rules

List all available rules:

```bash
editai list-rules rules/
```

View a specific rule:

```bash
editai view-rule rules/ rule_name
```

## Best Practices

1. **Keep rules focused** - Create separate rules for different types of edits
2. **Include examples** - Give clear before/after examples to guide the AI
3. **Test with `--dry-run`** - Preview changes before applying them
4. **Order matters** - Rules are applied in alphabetical order by filename
5. **Name consistently** - Use descriptive filenames like `passive_voice.md`
6. **Maintain a rules library** - Create a repository of standard rules for your team
7. **Update regularly** - Refine rules based on results and evolving style guidelines

## Limitations

- The AI may occasionally misinterpret ambiguous instructions
- Complex transformations might require multiple passes
- Very context-dependent changes may occasionally miss the mark

## Advanced Usage

### Rule Prioritization

Rules are applied in alphabetical order by filename. To control the order:

```
01_first_rule.md
02_second_rule.md
03_third_rule.md
```

### Conditional Rules

Create rules that only apply in specific contexts:

```markdown
# Rule: api_documentation

Only apply these changes to sections of the document that describe API endpoints.

For API endpoint documentation sections:
1. Ensure each endpoint starts with a heading formatted as "## GET /path" or "## POST /path"
2. Make sure each endpoint has a "Parameters" section and a "Response" section
3. Format all parameter lists as tables with Name, Type, Required, and Description columns
```

### Testing Rule Effectiveness

To evaluate how well a rule works:

1. Create a test document with examples of the patterns you want to fix
2. Run the rule with `--dry-run` to see the changes
3. Iterate on the rule instructions to improve results
4. Document successful patterns in your rule