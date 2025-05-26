from pathlib import Path
from typing import List, Optional
import glob

import typer
from rich.console import Console
from rich.progress import Progress, TaskID

from .approval import EditorApprovalLog
from .config import DEFAULT_CONFIG_PATH, create_default_config, load_config
from .editors.custom_rules import RulesEditor
from .editors.vale import ValeEditor

console = Console()

def collect_files(
    path: str, 
    recursive: bool = False, 
    include_patterns: List[str] = None, 
    exclude_patterns: List[str] = None
) -> List[Path]:
    """
    Collect markdown files from a path (file or directory).
    
    Args:
        path: File path, directory path, or glob pattern
        recursive: Whether to search directories recursively
        include_patterns: List of glob patterns to include
        exclude_patterns: List of glob patterns to exclude
        
    Returns:
        List of Path objects for markdown files
    """
    path_obj = Path(path)
    files = []
    
    # If it's a file, return it directly
    if path_obj.is_file():
        if path_obj.suffix in ['.md', '.mdx']:
            return [path_obj]
        else:
            console.print(f"[yellow]Warning: {path} is not a markdown file[/yellow]")
            return []
    
    # If it's a directory, find markdown files
    elif path_obj.is_dir():
        if recursive:
            files.extend(path_obj.rglob("*.md"))
            files.extend(path_obj.rglob("*.mdx"))
        else:
            files.extend(path_obj.glob("*.md"))
            files.extend(path_obj.glob("*.mdx"))
    
    # If it's a glob pattern, expand it
    else:
        expanded = glob.glob(path, recursive=recursive)
        for p in expanded:
            p_obj = Path(p)
            if p_obj.is_file() and p_obj.suffix in ['.md', '.mdx']:
                files.append(p_obj)
    
    # Apply include patterns
    if include_patterns:
        filtered_files = []
        for file in files:
            for pattern in include_patterns:
                if file.match(pattern):
                    filtered_files.append(file)
                    break
        files = filtered_files
    
    # Apply exclude patterns
    if exclude_patterns:
        filtered_files = []
        for file in files:
            excluded = False
            for pattern in exclude_patterns:
                if file.match(pattern):
                    excluded = True
                    break
            if not excluded:
                filtered_files.append(file)
        files = filtered_files
    
    return sorted(set(files))

app = typer.Typer(
    help="""
Hyperlint: A CLI tool for editing and improving Markdown files.

Available Commands:
- vale: Apply Vale linting to markdown files
- rules: Manage and apply custom editing rules
- config: Manage Hyperlint configuration
""",
    no_args_is_help=True,
)


# Create rules subcommand group
edit_app = typer.Typer(
    help="Apply rules",
    no_args_is_help=True,
)
app.add_typer(edit_app, name="apply")


@edit_app.command(name="vale")
def vale(
    path: str,
    vale_config_path: str | None = None,
    dry_run: bool = False,
    require_approval: bool = True,
    log_approvals: bool = True,
    config_path: Optional[Path] = None,
    recursive: bool = False,
    include: List[str] = typer.Option([], help="Include files matching these patterns"),
    exclude: List[str] = typer.Option([], help="Exclude files matching these patterns"),
):
    """
    Run Vale on markdown files to identify style issues.

    Examples:
        # Process a single file
        hyperlint apply vale docs/guide.md

        # Process all markdown files in a directory
        hyperlint apply vale docs/ --recursive

        # Process with glob pattern
        hyperlint apply vale "docs/**/*.md"

        # Process with custom Vale configuration
        hyperlint apply vale guide.md --vale-config-path .vale.ini

        # Preview changes without applying them
        hyperlint apply vale README.md --dry-run

        # Apply changes without approval prompts
        hyperlint apply vale README.md --no-require-approval

        # Include/exclude specific patterns
        hyperlint apply vale docs/ --recursive --exclude "draft_*.md" --include "*.md"
    """
    # Collect files to process
    files = collect_files(path, recursive, include or None, exclude or None)
    
    if not files:
        console.print(f"[yellow]No markdown files found for path: {path}[/yellow]")
        return
    
    # Load configuration
    config = load_config(config_path)

    # Override config values with CLI parameters
    if dry_run:
        config.dry_run = True

    # Process files
    if len(files) == 1:
        # Single file - use existing logic
        editor = ValeEditor(path=files[0], config=config)
        if config.dry_run:
            editor.dry_run()
        else:
            editor.update_file()
    else:
        # Multiple files - batch processing
        console.print(f"[blue]Processing {len(files)} files...[/blue]")
        
        success_count = 0
        error_count = 0
        
        with Progress() as progress:
            task = progress.add_task("Processing files...", total=len(files))
            
            for file_path in files:
                try:
                    progress.console.print(f"Processing: {file_path}")
                    editor = ValeEditor(path=file_path, config=config)
                    if config.dry_run:
                        editor.dry_run()
                    else:
                        editor.update_file()
                    success_count += 1
                except Exception as e:
                    console.print(f"[red]Error processing {file_path}: {e}[/red]")
                    error_count += 1
                finally:
                    progress.advance(task)
        
        console.print(f"[green]Completed: {success_count} files processed successfully[/green]")
        if error_count > 0:
            console.print(f"[red]Errors: {error_count} files failed[/red]")


@edit_app.command(name="rules")
def apply_rules(
    path: str,
    rules_directory: str,
    include_rules: List[str] = [],
    exclude_rules: List[str] = [],
    dry_run: bool = False,
    require_approval: bool = True,
    log_approvals: bool = True,
    config_path: Optional[Path] = None,
    recursive: bool = False,
    include: List[str] = typer.Option([], help="Include files matching these patterns"),
    exclude: List[str] = typer.Option([], help="Exclude files matching these patterns"),
):
    """
    Apply AI-powered rules to markdown documents.

    Rules are markdown files containing instructions for specific edits.
    Each rule is processed using AI to apply the specified changes.

    Examples:
        # Apply all rules to a single file
        hyperlint apply rules docs/guide.md rules/

        # Apply rules to all markdown files in a directory
        hyperlint apply rules docs/ rules/ --recursive

        # Apply with glob pattern
        hyperlint apply rules "docs/**/*.md" rules/

        # Apply specific rules to a file
        hyperlint apply rules README.md rules/ --include-rules passive_voice,bullet_consistency

        # Exclude specific rules
        hyperlint apply rules docs/guide.md rules/ --exclude-rules deprecated_terms

        # Preview rule application without making changes
        hyperlint apply rules docs/guide.md rules/ --dry-run

        # Include/exclude specific file patterns
        hyperlint apply rules docs/ rules/ --recursive --exclude "draft_*.md"
    """
    # Collect files to process
    files = collect_files(path, recursive, include or None, exclude or None)
    
    if not files:
        console.print(f"[yellow]No markdown files found for path: {path}[/yellow]")
        return
    
    # Load configuration
    config = load_config(config_path)

    # Override config values with CLI parameters
    if dry_run:
        config.dry_run = True
    if require_approval is not None:
        config.approval_mode = require_approval
    
    # Always set rules directory since it's now required
    config.custom_rules.rules_directory = Path(rules_directory)

    # Handle include_rules and exclude_rules list parsing
    include_list = []
    exclude_list = []

    if include_rules:
        if len(include_rules) == 1 and "," in include_rules[0]:
            include_list = include_rules[0].split(",")
        else:
            include_list = include_rules

    if include_list:
        config.custom_rules.include_rules = include_list

    if exclude_rules:
        if len(exclude_rules) == 1 and "," in exclude_rules[0]:
            exclude_list = exclude_rules[0].split(",")
        else:
            exclude_list = exclude_rules

    if exclude_list:
        config.custom_rules.exclude_rules = exclude_rules

    # Process files
    if len(files) == 1:
        # Single file - use existing logic
        editor = RulesEditor(
            path=files[0], 
            config=config,
            rules_directory=Path(rules_directory),
            include_rules=include_list,
            exclude_rules=exclude_list,
            dry_run=dry_run
        )

        if config.dry_run:
            editor.dry_run()
        else:
            editor.update_file()
    else:
        # Multiple files - batch processing
        console.print(f"[blue]Processing {len(files)} files with rules...[/blue]")
        
        success_count = 0
        error_count = 0
        
        with Progress() as progress:
            task = progress.add_task("Processing files...", total=len(files))
            
            for file_path in files:
                try:
                    progress.console.print(f"Processing: {file_path}")
                    editor = RulesEditor(
                        path=file_path, 
                        config=config,
                        rules_directory=Path(rules_directory),
                        include_rules=include_list,
                        exclude_rules=exclude_list,
                        dry_run=dry_run
                    )
                    
                    if config.dry_run:
                        editor.dry_run()
                    else:
                        editor.update_file()
                    success_count += 1
                except Exception as e:
                    console.print(f"[red]Error processing {file_path}: {e}[/red]")
                    error_count += 1
                finally:
                    progress.advance(task)
        
        console.print(f"[green]Completed: {success_count} files processed successfully[/green]")
        if error_count > 0:
            console.print(f"[red]Errors: {error_count} files failed[/red]")


# Create rules subcommand group
rules_app = typer.Typer(
    help="Manage and apply custom editing rules",
    no_args_is_help=True,
)
app.add_typer(rules_app, name="manage-rules")


@rules_app.command(name="list")
def list_rules(rules_directory: str):
    """
    List all available rules in the directory.

    Examples:
        # List all rules in the default rules directory
        hyperlint rules list rules/

        # List rules in a custom directory
        hyperlint rules list custom-rules/
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


@rules_app.command(name="view")
def view_rule(rules_directory: str, rule_name: str):
    """
    Display the content of a specific rule.

    Examples:
        # View a specific rule by name (with or without .md extension)
        hyperlint rules view rules/ passive_voice

        # View a rule in a custom directory
        hyperlint rules view custom-rules/ bullet_consistency.md
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


@rules_app.command(name="create")
def create_rule(rules_directory: str, rule_name: str):
    """
    Create a new empty rule file with a template.

    The created rule will include a basic structure with examples
    of common rule types that you can customize.

    Examples:
        # Create a new rule in the default rules directory
        hyperlint rules create rules/ passive_voice

        # Create a rule in a custom directory (extension optional)
        hyperlint rules create custom-rules/ bullet_consistency.md
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


@config_app.command(name="init")
def init_config():
    config_path = Path(DEFAULT_CONFIG_PATH)
    if config_path.exists():
        print(f"Error: Configuration already exists: {config_path}")
        raise typer.Exit(code=1)
    try:
        create_default_config(config_path)
        print(f"Created configuration: {config_path}")
    except Exception as e:
        print(f"Error creating configuration: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
