from pathlib import Path
from typing import List, Optional

import typer
from smolcrawl import list_indices as list_indices_from_smolcrawl

from .editors.ai import AIEditor
from .editors.arbitrary_links import ArbitraryLinkEditor
from .editors.custom_rules import CustomRuleEditor
from .editors.images import ImageAdditionEditor
from .editors.links import InternalLinkEditor
from .editors.vale import ValeEditor
from .utils import get_vale_config_path

app = typer.Typer()


@app.command()
def vale(path: str, vale_config_path: str | None = None):
    path_obj = Path(path)
    vale_config_path_final: Path
    if vale_config_path is None:
        maybe_path = get_vale_config_path()
        if maybe_path is None:
            print("Error: Vale config path could not be determined.")
            raise typer.Exit(code=1)
        vale_config_path_final = maybe_path
    else:
        vale_config_path_final = Path(vale_config_path)

    editor = ValeEditor(path=path_obj, vale_config_path=vale_config_path_final)
    print(editor.generate_v2())


@app.command()
def list_indices():
    list_indices_from_smolcrawl()


@app.command()
def links(path: str, local_index_names: List[str] = [], websearch: bool = False):
    path_obj = Path(path)
    if len(local_index_names) == 1:
        local_index_names = local_index_names[0].split(",")
    editor = InternalLinkEditor(path=path_obj, indexes=local_index_names)
    print(editor.generate_v2())


@app.command()
def add_images(
    path: str,
    image_folder_path: str,
    image_url_prefix: str = "/images",
):
    """Adds images found in image_folder_path to the document at path."""
    path_obj = Path(path)
    image_folder_path_obj = Path(image_folder_path)

    editor = ImageAdditionEditor(
        path=path_obj,
        image_folder_path=image_folder_path_obj,
        image_url_prefix=image_url_prefix,
    )
    print(editor.generate_v2())


@app.command()
def ai(path: str):
    path_obj = Path(path)
    editor = AIEditor(path=path_obj)
    print(editor.generate_v2())


@app.command()
def arbitrary_links(path: str):
    """
    Interactive REPL to add arbitrary links to a document.
    Prompts for URLs and descriptions, then finds the best placement for each link.
    """
    path_obj = Path(path)
    editor = ArbitraryLinkEditor(path=path_obj)
    print(editor.generate_v2())


@app.command()
def custom_rules(
    path: str, 
    rules_directory: str,
    include_rules: Optional[List[str]] = None,
    exclude_rules: Optional[List[str]] = None,
    dry_run: bool = False
):
    """Apply custom plaintext markdown rules from a directory to the document."""
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
    
    editor = CustomRuleEditor(
        path=path_obj,
        rules_directory=rules_dir_obj,
        include_rules=include_list,
        exclude_rules=exclude_list,
        dry_run=dry_run
    )
    
    print(editor.generate_v2())


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
