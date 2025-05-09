from pathlib import Path
import os
from typing import List, Optional, Union

import typer
from loguru import logger
from pydantic import DirectoryPath
from smolcrawl import list_indices as list_indices_from_smolcrawl

from .editors.ai import AIEditor
from .editors.arbitrary_links import ArbitraryLinkEditor
from .editors.custom_rules import CustomRuleEditor
from .editors.folder_processor import FolderProcessor
from .editors.images import ImageAdditionEditor
from .editors.links import InternalLinkEditor
from .editors.vale import ValeEditor
from .utils import get_vale_config_path

app = typer.Typer()


def is_directory(path: str) -> bool:
    """Check if a path is a directory."""
    return os.path.isdir(path)


@app.command()
def vale(
    path: str,
    vale_config_path: str | None = None,
    recursive: bool = False,
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = None,
    dry_run: bool = False
):
    """
    Run Vale on file(s) to identify style issues.

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.
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
            recursive=recursive
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
            with open(path_obj, 'w') as f:
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
    dry_run: bool = False
):
    """
    Add internal links to document(s).

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.
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
            recursive=recursive
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
            with open(path_obj, 'w') as f:
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
    recursive: bool = False,
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = None,
    dry_run: bool = False
):
    """
    Add images to document(s).

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.
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
                "image_url_prefix": image_url_prefix
            },
            include_pattern=include_pattern,
            exclude_patterns=exclude_patterns or [],
            recursive=recursive
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
        )
        processed_content = editor.generate_v2()

        if not dry_run:
            with open(path_obj, 'w') as f:
                f.write(processed_content)
            print(f"Processed file: {path_obj}")
        else:
            print(f"Dry run - would update {path_obj}")
            print(processed_content)


@app.command()
def ai(
    path: str,
    recursive: bool = False,
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = None,
    dry_run: bool = False
):
    """
    Use AI to improve document(s).

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.
    """
    path_obj = Path(path)

    if is_directory(path):
        # Process directory
        processor = FolderProcessor(
            directory_path=path_obj,
            editor_class=AIEditor,
            editor_kwargs={},
            include_pattern=include_pattern,
            exclude_patterns=exclude_patterns or [],
            recursive=recursive
        )
        results = processor.process_directory(dry_run=dry_run)

        # Print summary
        if not dry_run:
            print(f"Processed {len(results)} files with AI editor.")
        else:
            print(f"Dry run - would process {len(results)} files with AI editor.")
    else:
        # Process single file
        editor = AIEditor(path=path_obj)
        processed_content = editor.generate_v2()

        if not dry_run:
            with open(path_obj, 'w') as f:
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
    include_rules: Optional[List[str]] = None,
    exclude_rules: Optional[List[str]] = None,
    recursive: bool = False,
    include_pattern: str = "*.md",
    exclude_patterns: List[str] = None,
    dry_run: bool = False
):
    """
    Apply custom plaintext markdown rules to document(s).

    If path is a directory, process all markdown files in the directory.
    Otherwise, process the single file at path.
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
            editor_class=CustomRuleEditor,
            editor_kwargs={
                "rules_directory": rules_dir_obj,
                "include_rules": include_list,
                "exclude_rules": exclude_list,
                "dry_run": dry_run
            },
            include_pattern=include_pattern,
            exclude_patterns=exclude_patterns or [],
            recursive=recursive
        )
        results = processor.process_directory(dry_run=dry_run)

        # Print summary
        if not dry_run:
            print(f"Processed {len(results)} files with custom rules.")
        else:
            print(f"Dry run - would process {len(results)} files with custom rules.")
    else:
        # Process single file
        editor = CustomRuleEditor(
            path=path_obj,
            rules_directory=rules_dir_obj,
            include_rules=include_list,
            exclude_rules=exclude_list,
            dry_run=dry_run
        )

        processed_content = editor.generate_v2()

        if not dry_run:
            with open(path_obj, 'w') as f:
                f.write(processed_content)
            print(f"Processed file: {path_obj}")
        else:
            print(f"Dry run - would update {path_obj}")
            print(processed_content)


@app.command()
def list_rules(rules_directory: str):
    """List all available rules in the directory."""
    rules_dir_obj = Path(rules_directory)

    if not rules_dir_obj.exists() or not rules_dir_obj.is_dir():
        print(f"Error: Rules directory does not exist or is not a directory: {rules_directory}")
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
    """Display the content of a specific rule."""
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
    """Create a new empty rule file."""
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


if __name__ == "__main__":
    app()
