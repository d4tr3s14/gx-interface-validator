"""Layouts (File Definitions) de las interfaces, en formato YAML."""
from pathlib import Path

LAYOUTS_DIR = Path(__file__).parent


def layout_path(name: str) -> Path:
    """Devuelve la ruta al archivo de layout `<name>.yml`."""
    return LAYOUTS_DIR / f"{name}.yml"
