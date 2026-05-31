"""Rutas y configuración por defecto del proyecto (todas sobreescribibles)."""
from __future__ import annotations

import os
from pathlib import Path

# Raíz del repositorio (…/src/interface_validator/config.py -> sube 3 niveles)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTATIONS_DIR = Path(os.getenv("IV_EXPECTATIONS_DIR", PROJECT_ROOT / "expectations"))
DATA_DIR = Path(os.getenv("IV_DATA_DIR", PROJECT_ROOT / "data" / "sample"))
OUTPUT_DIR = Path(os.getenv("IV_OUTPUT_DIR", PROJECT_ROOT / "output"))

# Orden de secciones en los reportes
SECTION_ORDER = ("header", "body", "footer", "cross_section")
