"""Motor de validación: ejecuta suites de expectativas con Great Expectations 1.x."""
import os

# Silencia las barras de progreso (tqdm) y la analítica de GE para una
# salida limpia en CLI / CI.
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")

from .ge_runner import GeSectionRunner, run_section  # noqa: E402

__all__ = ["GeSectionRunner", "run_section"]
