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

# URLs de las vistas técnicas/interactivas (enlazadas desde el informe de proyecto).
METABASE_URL = os.getenv("METABASE_URL", "http://localhost:3000")
ALLURE_URL = os.getenv("ALLURE_URL", "https://d4tr3s14.github.io/gx-interface-validator/")

# Criterios de certificación del informe de proyecto.
#  - cada interfaz validada debe alcanzar este % de aprobación
#  - cada comparación debe quedar en/bajo esta cantidad de diferencias
CERT_MIN_VALIDATION_PERCENT = float(os.getenv("CERT_MIN_VALIDATION_PERCENT", "100"))
CERT_MAX_COMPARISON_DIFFS = int(os.getenv("CERT_MAX_COMPARISON_DIFFS", "0"))
