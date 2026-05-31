"""Tests de la segunda interfaz de ejemplo (SAMPLE02 - saldos)."""
from interface_validator.config import DATA_DIR
from interface_validator.service import validate_interface


def test_sample02_parses_and_passes():
    doc = validate_interface(
        DATA_DIR / "SAMPLE02_F20250404.FC", layout_name="sample02", write=False
    )
    assert doc["interface"] == "SAMPLE02"
    assert doc["summary"]["success"] is True
    assert set(doc["sections"]) == {"header", "body", "footer", "cross_section"}


def test_sample02_business_rules_run():
    doc = validate_interface(
        DATA_DIR / "SAMPLE02_F20250404.FC", layout_name="sample02", write=False
    )
    cross = doc["sections"]["cross_section"]
    # Dos reglas de negocio declaradas en el layout (conteo y suma de saldos)
    assert cross["statistics"]["evaluated_expectations"] == 2
    assert cross["success"] is True
