from pathlib import Path
from typing import List

import typer
from smolcrawl import list_indices as list_indices_from_smolcrawl

from .editors.ai import AIEditor
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


if __name__ == "__main__":
    app()
