import concurrent.futures
import os
from pathlib import Path
from typing import List

import typer
from loguru import logger

from .config import SimpleConfig, create_default_config, find_config_file
from .editors.vale import ValeEditor
from .utils import get_vale_config_path

app = typer.Typer(
    help="""
EditAI: A CLI tool for editing and improving Markdown documentation.

Available Commands:
- vale: Apply Vale linting to markdown files
- custom-rules: Apply AI-powered editing rules
- list-rules: Show available custom rules
- view-rule: Display contents of a specific rule
- create-rule: Create a new custom rule
""",
    no_args_is_help=True,
)


def is_directory(path: str) -> bool:
    """Check if a path is a directory."""
    return os.path.isdir(path)


@app.command()
def vale(
    path: str,
    vale_config_path: str | None = None,
    recursive: bool = False,
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = [],
    dry_run: bool = False,
):
    """
    Run Vale on file(s) to identify style issues.

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.

    Examples:
        # Process a single file
        editai vale docs/guide.md

        # Process a directory with custom Vale configuration
        editai vale docs/ --vale-config-path .vale.ini --recursive

        # Preview changes without applying them
        editai vale README.md --dry-run

        # Process only specific files in a directory
        editai vale docs/ --include-pattern "*.md" --exclude-patterns "draft/*,temp/*"
    """
    path_obj = Path(path)

    # Determine Vale config path
    vale_config_path_final: Path
    if vale_config_path is None:
        maybe_path = get_vale_config_path()
        if maybe_path is None:
            print("Error: Vale config path could not be determined.")
            raise typer.Exit(code=1)
        vale_config_path_final = maybe_path
    else:
        vale_config_path_final = Path(vale_config_path)

    if is_directory(path):
        # Process directory
        processor = FolderProcessor(
            directory_path=path_obj,
            editor_class=ValeEditor,
            editor_kwargs={"vale_config_path": vale_config_path_final},
            include_pattern=include_pattern,
            exclude_patterns=exclude_patterns or [],
            recursive=recursive,
        )
        results = processor.process_directory(dry_run=dry_run)

        # Print summary
        if not dry_run:
            print(f"Processed {len(results)} files with Vale.")
        else:
            print(f"Dry run - would process {len(results)} files with Vale.")
    else:
        # Process single file
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
def list_indices():
    list_indices_from_smolcrawl()


@app.command()
def links(
    path: str,
    local_index_names: List[str] = [],
    websearch: bool = False,
    recursive: bool = False,
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = None,
    dry_run: bool = False,
):
    """
    Add internal links to document(s).

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.

    Examples:
        # Process a single file using the default index
        editai links docs/getting-started.md

        # Process a directory with specific indices
        editai links docs/ --local-index-names api-docs,user-guide --recursive

        # Process a file with web search for external resources
        editai links README.md --websearch

        # Preview changes without applying them
        editai links docs/ --dry-run --recursive

        # Process only markdown files excluding certain folders
        editai links src/ --include-pattern "*.md" --exclude-patterns "drafts/*,archive/*"
    """
    path_obj = Path(path)

    # Parse comma-separated list of indexes
    if len(local_index_names) == 1 and "," in local_index_names[0]:
        local_index_names = local_index_names[0].split(",")

    if is_directory(path):
        # Process directory
        processor = FolderProcessor(
            directory_path=path_obj,
            editor_class=InternalLinkEditor,
            editor_kwargs={"indexes": local_index_names},
            include_pattern=include_pattern,
            exclude_patterns=exclude_patterns or [],
            recursive=recursive,
        )
        results = processor.process_directory(dry_run=dry_run)

        # Print summary
        if not dry_run:
            print(f"Processed {len(results)} files with internal links.")
        else:
            print(f"Dry run - would process {len(results)} files with internal links.")
    else:
        # Process single file
        editor = InternalLinkEditor(path=path_obj, indexes=local_index_names)
        processed_content = editor.generate_v2()

        if not dry_run:
            with open(path_obj, "w") as f:
                f.write(processed_content)
            print(f"Processed file: {path_obj}")
        else:
            print(f"Dry run - would update {path_obj}")
            print(processed_content)


@app.command()
def add_images(
    path: str,
    image_folder_path: str,
    image_url_prefix: str = "/images",
    caption_model: str = typer.Option(
        "claude-3-haiku-20240307", help="Model to use for generating image captions"
    ),
    location_model: str = typer.Option(
        "claude-3-opus-20240229", help="Model to use for determining image placement"
    ),
    name_model: str = typer.Option(
        "claude-3-haiku-20240307", help="Model to use for generating image filenames"
    ),
    amble_model: str = typer.Option(
        "claude-3-haiku-20240307", help="Model to use for generating text around images"
    ),
    recursive: bool = False,
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = None,
    dry_run: bool = False,
):
    """
    Add images to document(s).

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.

    The image editor uses AI models to:
    - Generate descriptive captions for image alt text
    - Create optimized filenames for images
    - Determine the best placement for images in the document
    - Generate appropriate text introducing and following images

    Examples:
        # Add images to a single file
        editai add-images docs/tutorial.md images/

        # Add images to documents in a directory with a custom URL prefix
        editai add-images docs/ assets/ --image-url-prefix /assets --recursive

        # Preview image additions without applying them
        editai add-images README.md images/ --dry-run

        # Process specific files in a directory
        editai add-images docs/ images/ --include-pattern "guide-*.md" --recursive

        # Add images using a CDN URL prefix
        editai add-images docs/tutorial.md images/ --image-url-prefix https://cdn.example.com/images

        # Use different AI models for image processing
        editai add-images docs/tutorial.md images/ --caption-model "anthropic/claude-3-sonnet-20240229" --location-model "anthropic/claude-3-opus-20240229"

        # Use smaller models for faster processing
        editai add-images docs/tutorial.md images/ --caption-model "anthropic/claude-3-haiku-20240307" --name-model "anthropic/claude-3-haiku-20240307"
    """
    path_obj = Path(path)
    image_folder_path_obj = Path(image_folder_path)

    if is_directory(path):
        # Process directory
        processor = FolderProcessor(
            directory_path=path_obj,
            editor_class=ImageAdditionEditor,
            editor_kwargs={
                "image_folder_path": image_folder_path_obj,
                "image_url_prefix": image_url_prefix,
                "caption_model": caption_model,
                "name_model": name_model,
                "location_model": location_model,
                "amble_model": amble_model,
            },
            include_pattern=include_pattern,
            exclude_patterns=exclude_patterns or [],
            recursive=recursive,
        )
        results = processor.process_directory(dry_run=dry_run)

        # Print summary
        if not dry_run:
            print(f"Processed {len(results)} files with image additions.")
        else:
            print(f"Dry run - would process {len(results)} files with image additions.")
    else:
        # Process single file
        editor = ImageAdditionEditor(
            path=path_obj,
            image_folder_path=image_folder_path_obj,
            image_url_prefix=image_url_prefix,
            caption_model=caption_model,
            name_model=name_model,
            location_model=location_model,
            amble_model=amble_model,
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
def arbitrary_links(path: str):
    """
    Interactive REPL to add arbitrary links to a document.
    Prompts for URLs and descriptions, then finds the best placement for each link.

    Note: This command doesn't support directory processing since it's interactive.

    The REPL interface supports these commands:
    - Enter a URL followed by an optional description to add a link
    - Type 'exit' or 'quit' to exit the REPL and save changes
    - Type 'abort' to exit without saving

    Examples:
        # Start interactive link addition for a document
        editai arbitrary-links docs/getting-started.md

        # Within the REPL session:
        > https://example.com/api API Documentation
        > https://github.com/project-repo GitHub Repository
        > exit
    """
    path_obj = Path(path)

    if is_directory(path):
        print("Error: arbitrary_links command doesn't support directory processing.")
        print("Please specify a single file path instead.")
        raise typer.Exit(code=1)

    editor = ArbitraryLinkEditor(path=path_obj)
    print(editor.generate_v2())


@app.command()
def custom_rules(
    path: str,
    rules_directory: str,
    exclude_patterns: List[str] = [],
    exclude_patterns: List[str] = [],
    recursive: bool = False,
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = None,
    dry_run: bool = False,
    model: str = "anthropic/claude-3-haiku-20240307",
):
    """
    Apply AI-powered rules to document(s).

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.

    Rules are markdown files containing instructions for specific edits.
    Each rule is processed using AI to apply the specified changes.

    Examples:
        # Apply all rules to a single file
        editai custom-rules docs/guide.md rules/

        # Apply specific rules to a file
        editai custom-rules README.md rules/ --include-rules passive_voice,bullet_consistency

        # Exclude specific rules
        editai custom-rules docs/guide.md rules/ --exclude-rules deprecated_terms

        # Preview rule application without making changes
        editai custom-rules docs/guide.md rules/ --dry-run

        # Process all files in a directory recursively
        editai custom-rules docs/ rules/ --recursive

        # Process specific files in a directory
        editai custom-rules docs/ rules/ --include-pattern "*.md" --exclude-patterns "drafts/*"
    """
    path_obj = Path(path)
    rules_dir_obj = Path(rules_directory)

    # Handle include_rules and exclude_rules list parsing
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

    if is_directory(path):
        # Process directory
        processor = FolderProcessor(
            directory_path=path_obj,
            editor_class=RulesEditor,
            editor_kwargs={
                "rules_directory": rules_dir_obj,
                "include_rules": include_list,
                "exclude_rules": exclude_list,
                "dry_run": dry_run,
                "model": model,
            },
            include_pattern=include_pattern,
            exclude_patterns=exclude_patterns or [],
            recursive=recursive,
        )
        results = processor.process_directory(dry_run=dry_run)

        # Print summary
        if not dry_run:
            print(f"Processed {len(results)} files with custom rules.")
        else:
            print(f"Dry run - would process {len(results)} files with custom rules.")
    else:
        # Process single file
        editor = RulesEditor(
            path=path_obj,
            rules_directory=rules_dir_obj,
            include_rules=include_list,
            exclude_rules=exclude_list,
            dry_run=dry_run,
            model=model,
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


@app.command()
def edit(
    path: str,
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
    editors: Optional[List[str]] = typer.Option(
        None, "--editors", help="Comma-separated list of editors to run"
    ),
    exclude_editors: Optional[List[str]] = typer.Option(
        None, "--exclude", help="Comma-separated list of editors to exclude"
    ),
    recursive: Optional[bool] = typer.Option(None, "--recursive/--no-recursive"),
    dry_run: Optional[bool] = typer.Option(None, "--dry-run/--no-dry-run"),
    parallel: Optional[bool] = typer.Option(
        True, "--parallel/--sequential", help="Run editors in parallel"
    ),
    include_pattern: Optional[str] = typer.Option(None, "--include"),
    exclude_patterns: Optional[List[str]] = typer.Option(None, "--exclude-patterns"),
):
    """
    Run multiple editors on files in one operation.

    The edit command allows you to run any combination of editors
    (ai, vale, custom_rules, images, links) on your files, either
    in parallel (default) or sequentially.

    Configuration is loaded from either:
    1. The file specified with --config
    2. ./editai.yaml in the current directory
    3. ~/.config/editai/config.yaml

    CLI arguments override configuration file settings.

    Examples:
        # Run all editors on a markdown file
        editai edit README.md

        # Run specific editors on files in a directory
        editai edit docs/ --editors ai,vale,links --recursive

        # Run all editors except one
        editai edit docs/ --exclude custom_rules

        # Use a specific configuration file
        editai edit src/ --config ./custom-config.yaml

        # Run editors sequentially instead of in parallel
        editai edit docs/ --sequential

        # Preview changes without making modifications
        editai edit docs/ --dry-run
    """

    # Load configuration
    config_path = config or find_config_file()
    if config_path:
        logger.info(f"Loading configuration from {config_path}")
        config_obj = SimpleConfig.from_yaml(config_path)
    else:
        logger.info("No configuration file found, using defaults")
        config_obj = SimpleConfig()

    # Process editor selection
    all_editors = ["ai", "vale", "custom_rules", "images", "links"]

    if editors:
        selected_editors = [e.strip() for e in editors[0].split(",") if e.strip()]
    else:
        selected_editors = all_editors

    if exclude_editors:
        excluded = [e.strip() for e in exclude_editors[0].split(",") if e.strip()]
        selected_editors = [e for e in selected_editors if e not in excluded]

    # Merge CLI args with config
    cli_args = {
        "recursive": recursive,
        "dry_run": dry_run,
        "include_pattern": include_pattern,
        "exclude_patterns": exclude_patterns,
    }
    merged_config = config_obj.merge_with_cli(cli_args)

    # Run editors
    path_obj = Path(path)
    results = {}

    if parallel:
        # Run editors in parallel
        results = run_editors_parallel(
            path_obj, selected_editors, config_obj, merged_config
        )
    else:
        # Run editors sequentially
        results = run_editors_sequential(
            path_obj, selected_editors, config_obj, merged_config
        )

    # Print summary
    print_summary(results)


def run_editors_sequential(
    path: Path, editors: List[str], config: SimpleConfig, merged_config: Dict
) -> Dict[str, Any]:
    """Run editors one after another"""
    results = {}

    for editor_name in editors:
        try:
            result = run_single_editor(editor_name, path, config, merged_config)
            results[editor_name] = result
            logger.success(f"Completed {editor_name} editor")
        except Exception as e:
            logger.error(f"Error running {editor_name}: {e}")
            results[editor_name] = {"error": str(e)}

    return results


def run_editors_parallel(
    path: Path, editors: List[str], config: SimpleConfig, merged_config: Dict
) -> Dict[str, Any]:
    """Run editors in parallel"""
    results = {}

    with ThreadPoolExecutor(max_workers=len(editors)) as executor:
        future_to_editor = {
            executor.submit(run_single_editor, name, path, config, merged_config): name
            for name in editors
        }

        for future in concurrent.futures.as_completed(future_to_editor):
            editor_name = future_to_editor[future]
            try:
                result = future.result()
                results[editor_name] = result
                logger.success(f"Completed {editor_name} editor")
            except Exception as e:
                logger.error(f"Error running {editor_name}: {e}")
                results[editor_name] = {"error": str(e)}

    return results


def run_single_editor(
    editor_name: str, path: Path, config: SimpleConfig, merged_config: Dict
) -> Dict[str, Any]:
    """Run a single editor with given configuration"""

    # Get editor-specific config
    editor_config = config.get_editor_config(editor_name)

    # Map editor names to classes
    editor_mapping = {
        "vale": ValeEditor,
        "custom_rules": RulesEditor,
        "images": ImageAdditionEditor,
        "links": InternalLinkEditor,
    }

    editor_class = editor_mapping.get(editor_name)
    if not editor_class:
        raise ValueError(f"Unknown editor: {editor_name}")

    # Create editor with configuration
    editor_kwargs = editor_config.copy()

    # Handle special cases
    if editor_name == "custom_rules":
        editor_kwargs["rules_directory"] = Path(
            editor_config.get("rules_directory", "./rules")
        )
        editor_kwargs["include_rules"] = editor_config.get("enabled_rules", [])
        editor_kwargs["exclude_rules"] = editor_config.get("disabled_rules", [])

    if editor_name == "images":
        editor_kwargs["image_folder_path"] = guess_image_folder(path)
        editor_kwargs["image_url_prefix"] = editor_config.get(
            "default_url_prefix", "/images"
        )
        # Add model configuration
        editor_kwargs["caption_model"] = editor_config.get(
            "caption_generation", {}
        ).get("model", "claude-3-haiku-20240307")
        editor_kwargs["name_model"] = editor_config.get("name_generation", {}).get(
            "model", "claude-3-haiku-20240307"
        )
        editor_kwargs["location_model"] = editor_config.get(
            "location_detection", {}
        ).get("model", "claude-3-opus-20240229")
        editor_kwargs["amble_model"] = editor_config.get("amble_generation", {}).get(
            "model", "claude-3-haiku-20240307"
        )

    if editor_name == "vale":
        editor_kwargs["vale_config_path"] = Path(
            editor_config.get("config_path", "./.vale.ini")
        )

    if editor_name == "links":
        editor_kwargs["indexes"] = editor_config.get("default_indices", [])

    # Process files
    if path.is_dir() and merged_config.get("recursive", True):
        processor = FolderProcessor(
            directory_path=path,
            editor_class=editor_class,
            editor_kwargs=editor_kwargs,
            include_pattern=merged_config.get("include_pattern", "*.md"),
            exclude_patterns=merged_config.get("exclude_patterns", []),
            recursive=True,
        )
        file_results = processor.process_directory(
            dry_run=merged_config.get("dry_run", False)
        )
        return {"files_processed": len(file_results), "results": file_results}
    else:
        # Single file processing
        editor = editor_class(path=path, **editor_kwargs)
        result = editor.generate_v2()

        if not merged_config.get("dry_run", False):
            with open(path, "w") as f:
                f.write(result)

        return {"file": str(path), "modified": not merged_config.get("dry_run", False)}


def print_summary(results: Dict[str, Any]):
    """Print summary of editor results"""
    typer.echo("\n" + "=" * 50)
    typer.echo("EditAI Summary")
    typer.echo("=" * 50)

    for editor_name, result in results.items():
        typer.echo(f"\n{editor_name.upper()} Editor:")
        if "error" in result:
            typer.echo(f"  ❌ Error: {result['error']}", err=True)
        elif "files_processed" in result:
            typer.echo(f"  ✅ Processed {result['files_processed']} files")
        else:
            typer.echo(f"  ✅ Processed {result.get('file', 'file')}")

    typer.echo("\n" + "=" * 50)


# Add config subcommand for managing configurations
config_app = typer.Typer()
app.add_typer(config_app, name="config")


@config_app.command("init")
def init_config(
    path: Path = typer.Option(
        Path.cwd() / "editai.yaml", help="Configuration file path"
    ),
):
    """
    Create a default configuration file with examples of all settings.

    The configuration file contains settings for all editors and
    global options. You can edit this file to customize default behavior.

    Examples:
        # Create configuration in the current directory (default)
        editai config init

        # Create configuration at a specific path
        editai config init --path ~/projects/docs/editai.yaml

        # Create in the default location for system-wide configuration
        editai config init --path ~/.config/editai/config.yaml
    """

    if path.exists():
        if not typer.confirm(
            f"Configuration file already exists at {path}. Overwrite?"
        ):
            raise typer.Abort()

    created_path = create_default_config(path)
    typer.echo(f"Configuration created at {created_path}")


@config_app.command("show")
def show_config(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
):
    """
    Display the current configuration settings.

    Shows the contents of the configuration file that would be used
    by the edit command. This is useful for verifying your settings.

    Examples:
        # Show configuration from the default location
        editai config show

        # Show configuration from a specific file
        editai config show --config custom-editai.yaml
    """

    config_path = config or find_config_file()
    if not config_path:
        typer.echo("No configuration file found")
        raise typer.Exit(1)

    with open(config_path, "r") as f:
        content = f.read()

    typer.echo(f"Configuration from {config_path}:\n")
    typer.echo(content)


@config_app.command("validate")
def validate_config(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
):
    """
    Check if the configuration file is valid.

    Validates that the configuration file contains valid YAML and
    that all settings are correctly formatted. Use this after
    editing your configuration to check for syntax errors.

    Examples:
        # Validate the default configuration file
        editai config validate

        # Validate a specific configuration file
        editai config validate --config custom-editai.yaml
    """

    config_path = config or find_config_file()
    if not config_path:
        typer.echo("No configuration file found")
        raise typer.Exit(1)

    try:
        SimpleConfig.from_yaml(config_path)
        typer.echo("Configuration is valid ✅")
    except Exception as e:
        typer.echo(f"Configuration error: {e} ❌")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
