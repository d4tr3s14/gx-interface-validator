"""
Proyección de los resultados consolidados hacia Allure.

Cada sección se convierte en un paso (`allure.step`) y cada expectativa en un
sub-paso. Las expectativas fallidas se muestran como pasos rojos y adjuntan el
detalle (valores inesperados / observados) sin abortar el recorrido, de modo que
el reporte muestre TODAS las fallas de la interfaz, no solo la primera.
"""
from __future__ import annotations

import json

from . import taxonomy

try:
    import allure

    _ALLURE = True
except ImportError:  # permite usar el motor sin Allure (p. ej. desde el CLI)
    _ALLURE = False


def _label(result: dict) -> str:
    etype = result.get("expectation_type", "expectation")
    column = result.get("kwargs", {}).get("column")
    return f"{etype} [{column}]" if column else etype


def _failure_detail(section: str, result: dict) -> str:
    """Texto legible con el error específico (qué se esperaba y qué se encontró)."""
    category, subtype = taxonomy.categorize(result["expectation_type"], section)
    examples = taxonomy.error_examples(result)
    lines = [
        f"Categoría        : {category}",
        f"Validación       : {subtype}",
        f"Columna          : {taxonomy.column_of(result)}",
        f"Qué se esperaba  : {taxonomy.expected_text(result)}",
        f"Valor encontrado : {examples['found'] or '(no aplica)'}",
        f"Línea(s)         : {examples['lines'] or '(no aplica)'}",
        f"Datos afectados  : {taxonomy.error_count(result)}",
    ]
    return "\n".join(lines)


def _attach(name: str, payload: dict) -> None:
    if _ALLURE:
        allure.attach(
            json.dumps(payload, indent=2, ensure_ascii=False),
            name=name,
            attachment_type=allure.attachment_type.JSON,
        )


def collect_failures(document: dict) -> list[str]:
    """Devuelve una lista legible de las expectativas fallidas del documento."""
    failures: list[str] = []
    for section, block in document.get("sections", {}).items():
        for result in block.get("results", []):
            if not result.get("success", False):
                failures.append(f"{section}: {_label(result)}")
    return failures


def _report_expectation(section: str, result: dict, failures: list[str]) -> None:
    _, subtype = taxonomy.categorize(result["expectation_type"], section)
    column = result.get("kwargs", {}).get("column")
    step_name = f"{subtype} · {column}" if column else subtype

    if not _ALLURE:
        if not result.get("success", False):
            failures.append(f"{section}: {_label(result)}")
        return

    try:
        with allure.step(step_name):
            if not result.get("success", False):
                # Detalle legible: dónde está el error exactamente.
                if _ALLURE:
                    allure.attach(
                        _failure_detail(section, result),
                        name="¿Dónde está el error?",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                _attach("resultado técnico (GE)", result.get("result", {}))
                failures.append(f"{section}: {_label(result)}")
                raise AssertionError(step_name)
    except AssertionError:
        # Se traga la excepción para marcar el paso en rojo y continuar.
        pass


def _report_block(section: str, block: dict, failures: list[str]) -> None:
    stats = block.get("statistics", {})
    ok = stats.get("successful_expectations", 0)
    total = stats.get("evaluated_expectations", 0)
    if not _ALLURE:
        for result in block.get("results", []):
            if not result.get("success", False):
                failures.append(f"{section}: {_label(result)}")
        return
    with allure.step(f"Sección '{section}' — {ok}/{total} expectativas OK"):
        for result in block.get("results", []):
            _report_expectation(section, result, failures)


def report_section(document: dict, section: str) -> list[str]:
    """Proyecta UNA sección del documento en pasos de Allure y devuelve sus fallas."""
    failures: list[str] = []
    block = document.get("sections", {}).get(section)
    if block is None:
        return failures
    _report_block(section, block, failures)
    return failures


def attach_executive_report(document: dict, parsed=None, meta: dict | None = None) -> None:
    """Adjunta a Allure el MISMO informe ejecutivo HTML que ve el usuario."""
    if not _ALLURE:
        return
    from .html_report import render_html  # import perezoso (evita ciclos)

    html = render_html(document, meta=meta, parsed=parsed)
    allure.attach(
        html,
        name="Informe ejecutivo (vista de usuario)",
        attachment_type=allure.attachment_type.HTML,
    )


def report_document(document: dict) -> list[str]:
    """
    Proyecta el documento consolidado completo en pasos de Allure.

    Returns:
        Lista de expectativas fallidas (vacía si todo pasó).
    """
    failures: list[str] = []
    if not _ALLURE:
        return collect_failures(document)

    _attach("documento consolidado", document)
    for section, block in document.get("sections", {}).items():
        _report_block(section, block, failures)
    return failures
