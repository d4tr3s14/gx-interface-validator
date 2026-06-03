"""Configuración global de pytest: garantiza que existan los datos de ejemplo."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
SAMPLE_DIR = ROOT / "data" / "sample"
REQUIRED = [
    "SAMPLE01_F20250404.FC",
    "SAMPLE01_F20250402.FC",
    "SAMPLE02_F20250404.FC",
    "SAMPLE04_F20250404.FC",
]


@pytest.fixture(scope="session", autouse=True)
def ensure_sample_data():
    """Genera los archivos sintéticos si aún no existen."""
    if not all((SAMPLE_DIR / f).exists() for f in REQUIRED):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_sample_data.py")],
            check=True,
        )
    yield
