"""
Step definitions (pytest-bdd) para la validación de interfaces.

La capa Gherkin describe el contrato de negocio; cada paso delega el trabajo
pesado en el motor (Great Expectations) y proyecta el resultado en Allure.
"""
from __future__ import annotations

from pathlib import Path

import allure
from pytest_bdd import given, parsers, scenarios, then, when

from interface_validator import config
from interface_validator.reporting import attach_executive_report, report_section
from interface_validator.service import parse_and_validate

# Vincula TODOS los escenarios del .feature
scenarios("interface_validation.feature")


@given(parsers.parse('el archivo de interfaz "{file_name}"'), target_fixture="fc_file")
def fc_file(file_name: str) -> str:
    path = config.DATA_DIR / file_name
    assert path.exists(), f"No existe el archivo de interfaz: {path}"
    allure.dynamic.title(f"Validación de {file_name}")
    return str(path)


@when("valido la interfaz", target_fixture="document")
def validate(fc_file: str) -> dict:
    # El layout se infiere del prefijo del nombre (SAMPLE01_... -> sample01)
    layout_name = Path(fc_file).name.split("_")[0].lower()
    parsed, document = parse_and_validate(fc_file, layout_name=layout_name)
    summary = document["summary"]
    allure.attach(
        f"{summary['successful']}/{summary['total_expectations']} "
        f"expectativas OK ({summary['success_percent']}%)",
        name="resumen",
        attachment_type=allure.attachment_type.TEXT,
    )
    # Adjunta el MISMO informe ejecutivo HTML para el lector de negocio.
    attach_executive_report(document, parsed=parsed, meta={"system": layout_name.upper()})
    return document


@then(parsers.parse('la sección "{section}" cumple todas sus expectativas'))
def section_passes(document: dict, section: str):
    failures = report_section(document, section)
    assert not failures, "Expectativas fallidas:\n" + "\n".join(failures)


@then("las reglas de negocio cross-section se cumplen")
def cross_section_passes(document: dict):
    failures = report_section(document, "cross_section")
    assert not failures, "Reglas de negocio fallidas:\n" + "\n".join(failures)


@then("la interfaz se marca como fallida")
def interface_is_failed(document: dict):
    assert document["summary"]["success"] is False, "Se esperaba que la interfaz fallara"


@then(parsers.parse('se reportan expectativas fallidas en las secciones "{sections}"'))
def failures_reported(document: dict, sections: str):
    expected = [s.strip() for s in sections.split(",")]
    for section in expected:
        failures = report_section(document, section)
        assert failures, f"Se esperaban fallas en la sección '{section}' y no hubo"
