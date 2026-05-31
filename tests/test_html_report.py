"""Tests del generador de informe de cara al usuario."""
from interface_validator.config import DATA_DIR
from interface_validator.reporting import render_html
from interface_validator.reporting.html_report import build_model
from interface_validator.service import parse_and_validate


def _doc(name="SAMPLE01_F20250404.FC", layout="sample01"):
    return parse_and_validate(DATA_DIR / name, layout)


def test_model_for_valid_interface_is_approved():
    parsed, document = _doc()
    model = build_model(document, {"system": "DEMO"}, parsed=parsed)
    assert model["approved"] is True
    assert model["error_rows"] == []
    assert model["failed_details"] == []
    assert model["record_count"] == 8


def test_model_for_broken_interface_classifies_errors():
    parsed, document = _doc("SAMPLE01_F20250402.FC")
    model = build_model(document, {}, parsed=parsed)
    assert model["approved"] is False
    assert len(model["error_rows"]) > 0
    assert len(model["failed_details"]) > 0
    # Hay categorías de negocio entre los errores (totales del footer)
    categorias = {r["category"] for r in model["error_rows"]}
    assert "Negocio" in categorias


def test_render_html_contains_key_sections():
    parsed, document = _doc()
    html = render_html(document, meta={"system": "DEMO"}, parsed=parsed)
    assert "INFORME DE VALIDACIÓN DE INTERFACES" in html
    assert "VALIDACIONES EXITOSAS POR CATEGORÍA" in html
    assert "APROBADO" in html
    assert "<!DOCTYPE html>" in html
