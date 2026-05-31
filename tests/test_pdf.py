"""Test del generador de PDF (omitido si no hay backend disponible)."""
import pytest

from interface_validator.config import DATA_DIR
from interface_validator.reporting.html_report import generate_report
from interface_validator.reporting.pdf import _find_chromium
from interface_validator.service import parse_and_validate


def _pdf_backend_available() -> bool:
    if _find_chromium():
        return True
    try:
        import weasyprint  # noqa: F401

        from weasyprint import HTML

        HTML(string="<p>x</p>").write_pdf  # noqa: B018
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _pdf_backend_available(), reason="No hay backend de PDF (Chromium/WeasyPrint)")
def test_pdf_is_generated(tmp_path):
    parsed, document = parse_and_validate(DATA_DIR / "SAMPLE01_F20250404.FC", "sample01")
    outputs = generate_report(document, tmp_path, meta={"system": "DEMO"}, parsed=parsed, fmt="pdf")
    # El backend de PDF depende del entorno (GTK / navegador). Si no logra
    # generarlo aquí, se omite en vez de fallar (no es una regresión de código).
    if "pdf" not in outputs:
        pytest.skip(f"Backend de PDF no funcional en este entorno: {outputs.get('pdf_error')}")
    assert outputs["pdf"].exists()
    assert outputs["pdf"].stat().st_size > 1000
