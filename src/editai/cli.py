from pathlib import Path
from typing import List

import typer

from .editors.custom_rules import RulesEditor
from .editors.vale import ValeEditor
from .utils import get_vale_config_path

app = typer.Typer(
    help="""
EditAI: A CLI tool for editing and improving Markdown files.

Available Commands:
- vale: Apply Vale linting to a markdown file
- custom-rules: Apply AI-powered editing rules to a file
- list-rules: Show available custom rules
- view-rule: Display contents of a specific rule
- create-rule: Create a new custom rule
""",
    no_args_is_help=True,
)


@app.command()
def vale(
    path: str,
    vale_config_path: str | None = None,
    dry_run: bool = False,
):
    """
    Run Vale on a file to identify style issues.

    Examples:
        # Process a file
        editai vale docs/guide.md

        # Process with custom Vale configuration
        editai vale guide.md --vale-config-path .vale.ini

        # Preview changes without applying them
        editai vale README.md --dry-run
    """
    path_obj = Path(path)

    # Determine Vale config path
    vale_config_path_final: Path
    if vale_config_path is None:
        maybe_path = get_vale_config_path()
        if maybe_path is None:
            print("Error: Vale config path could not be determined.")
            raise typer.Exit(code=1)
        vale_config_path_final = Path(maybe_path)
    else:
        vale_config_path_final = Path(vale_config_path)

    editor = ValeEditor(path=path_obj, vale_config_path=vale_config_path_final)
    processed_content = editor.generate_v2()

    if not dry_run:
        with open(path_obj, "w") as f:
            f.write(processed_content)
        print(f"Processed file: {path_obj}")
    else:
        print(f"Dry run - would update {path_obj}")
        print(processed_content)


@app.command()
def custom_rules(
    path: str,
    rules_directory: str,
    include_rules: List[str] = [],
    exclude_rules: List[str] = [],
    dry_run: bool = False,
):
    """
    Apply AI-powered rules to a document.

    Rules are markdown files containing instructions for specific edits.
    Each rule is processed using AI to apply the specified changes.

    Examples:
        # Apply all rules to a file
        editai custom-rules docs/guide.md rules/

        # Apply specific rules to a file
        editai custom-rules README.md rules/ --include-rules passive_voice,bullet_consistency

        # Exclude specific rules
        editai custom-rules docs/guide.md rules/ --exclude-rules deprecated_terms

        # Preview rule application without making changes
        editai custom-rules docs/guide.md rules/ --dry-run
    """
    path_obj = Path(path)
    rules_dir_obj = Path(rules_directory)

    # Handle include_rules and exclude_rules list parsing
    include_list = []
    exclude_list = []

    include_list = []
    exclude_list = []

    if include_rules:
        if len(include_rules) == 1 and "," in include_rules[0]:
            include_list = include_rules[0].split(",")
        else:
            include_list = include_rules

    if exclude_rules:
        if len(exclude_rules) == 1 and "," in exclude_rules[0]:
            exclude_list = exclude_rules[0].split(",")
        else:
            exclude_list = exclude_rules

    editor = RulesEditor(
        path=path_obj,
        rules_directory=rules_dir_obj,
        include_rules=include_list,
        exclude_rules=exclude_list,
        dry_run=dry_run,
    )

    processed_content = editor.generate_v2()

    if not dry_run:
        with open(path_obj, "w") as f:
            f.write(processed_content)
        print(f"Processed file: {path_obj}")
    else:
        print(f"Dry run - would update {path_obj}")
        print(processed_content)


@app.command()
def list_rules(rules_directory: str):
    """
    List all available rules in the directory.

    Examples:
        # List all rules in the default rules directory
        editai list-rules rules/

        # List rules in a custom directory
        editai list-rules custom-rules/
    """
    rules_dir_obj = Path(rules_directory)

    if not rules_dir_obj.exists() or not rules_dir_obj.is_dir():
        print(
            f"Error: Rules directory does not exist or is not a directory: {rules_directory}"
        )
        raise typer.Exit(code=1)

    rules = list(rules_dir_obj.glob("*.md"))

    if not rules:
        print(f"No rules found in directory: {rules_directory}")
        return

    print(f"Found {len(rules)} rules in directory: {rules_directory}\n")
    for rule_path in sorted(rules):
        print(f"- {rule_path.stem}")


@app.command()
def view_rule(rules_directory: str, rule_name: str):
    """
    Display the content of a specific rule.

    Examples:
        # View a specific rule by name (with or without .md extension)
        editai view-rule rules/ passive_voice

        # View a rule in a custom directory
        editai view-rule custom-rules/ bullet_consistency.md
    """
    rules_dir_obj = Path(rules_directory)

    if not rule_name.endswith(".md"):
        rule_name = f"{rule_name}.md"

    rule_path = rules_dir_obj / rule_name

    if not rule_path.exists():
        print(f"Error: Rule not found: {rule_name}")
        raise typer.Exit(code=1)

    try:
        with open(rule_path, "r") as f:
            rule_content = f.read()
        print(f"--- Rule: {rule_path.stem} ---\n")
        print(rule_content)
    except Exception as e:
        print(f"Error reading rule: {e}")
        raise typer.Exit(code=1)


@app.command()
def create_rule(rules_directory: str, rule_name: str):
    """
    Create a new empty rule file with a template.

    The created rule will include a basic structure with examples
    of common rule types that you can customize.

    Examples:
        # Create a new rule in the default rules directory
        editai create-rule rules/ passive_voice

        # Create a rule in a custom directory (extension optional)
        editai create-rule custom-rules/ bullet_consistency.md
    """
    rules_dir_obj = Path(rules_directory)

    if not rules_dir_obj.exists():
        print(f"Creating rules directory: {rules_directory}")
        rules_dir_obj.mkdir(parents=True)

    if not rule_name.endswith(".md"):
        rule_name = f"{rule_name}.md"

    rule_path = rules_dir_obj / rule_name

    if rule_path.exists():
        print(f"Error: Rule already exists: {rule_name}")
        raise typer.Exit(code=1)

    try:
        with open(rule_path, "w") as f:
            f.write(f"""# Rule: {rule_path.stem}

Instructions for the rule go here. Describe the changes to make to the document.

Example:
- Find instances of passive voice and convert to active voice
- Ensure bullet points are consistently formatted
- Replace deprecated terminology with approved terms
""")
        print(f"Created rule: {rule_path}")
    except Exception as e:
        print(f"Error creating rule: {e}")
        raise typer.Exit(code=1)


# Add config subcommand for managing configurations
config_app = typer.Typer()
app.add_typer(config_app, name="config")


if __name__ == "__main__":
    app()
