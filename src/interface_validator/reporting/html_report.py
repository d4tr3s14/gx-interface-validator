"""
Generador del informe de cara al usuario (Product Owner / responsable).

A diferencia del reporte Allure (orientado al QA automatizador), este informe es
un documento autocontenido, en lenguaje de negocio, pensado como **evidencia**:
estado de certificación, validaciones exitosas por categoría, clasificación de
errores, gráfico y detalle de las expectativas fallidas.

Salida: HTML autocontenido (fácil de compartir e imprimir a PDF). Si está
instalado WeasyPrint, también puede exportar a PDF.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from . import taxonomy
from .styles import REPORT_CSS

MAX_BODY_SAMPLE = 50


# --------------------------------------------------------------------------- #
# Construcción del modelo del informe
# --------------------------------------------------------------------------- #
def _failed_indices(block: dict) -> set[int]:
    idx: set[int] = set()
    for r in block.get("results", []):
        if r.get("success"):
            continue
        res = r.get("result", {})
        for key in ("unexpected_index_list", "partial_unexpected_index_list"):
            for v in res.get(key, []) or []:
                if isinstance(v, int):
                    idx.add(v)
    return idx


def build_model(document: dict, meta: dict, parsed=None) -> dict:
    sections = document.get("sections", {})
    summary = document.get("summary", {})

    success_by_cat: dict[tuple, int] = defaultdict(int)
    errors_by_cat: dict[tuple, dict] = defaultdict(lambda: {"count": 0, "affected": 0})
    failed_details: list[dict] = []
    chart: dict[str, dict[str, int]] = defaultdict(lambda: {"ok": 0, "fail": 0})

    total_errors = 0
    for section, block in sections.items():
        for r in block.get("results", []):
            category, subtype = taxonomy.categorize(r["expectation_type"], section)
            if r.get("success"):
                success_by_cat[(category, subtype)] += 1
                chart[category]["ok"] += 1
            else:
                total_errors += 1
                key = (category, subtype)
                errors_by_cat[key]["count"] += 1
                errors_by_cat[key]["affected"] += taxonomy.error_count(r)
                chart[category]["fail"] += 1
                examples = taxonomy.error_examples(r)
                failed_details.append({
                    "subtype": subtype,
                    "column": taxonomy.column_of(r),
                    "expected": taxonomy.expected_text(r),
                    "found": examples["found"],
                    "lines": examples["lines"],
                    "errors": taxonomy.error_count(r),
                    "section": section,
                })

    # Tabla de éxitos por categoría (ordenada)
    success_rows = []
    grouped = defaultdict(list)
    for (category, subtype), count in success_by_cat.items():
        grouped[category].append((subtype, count))
    for category in taxonomy.CATEGORY_ORDER:
        for subtype, count in sorted(grouped.get(category, [])):
            success_rows.append({"category": category, "subtype": subtype, "count": count})

    # Tabla de clasificación de errores
    error_rows = []
    for (category, subtype), data in errors_by_cat.items():
        pct = round(data["count"] / total_errors * 100, 1) if total_errors else 0.0
        error_rows.append({
            "category": category, "subtype": subtype,
            "count": data["count"], "pct": pct, "affected": data["affected"],
        })
    error_rows.sort(key=lambda x: (-x["count"], x["category"]))

    # Datos del gráfico (barras CSS)
    chart_rows = []
    for category in taxonomy.CATEGORY_ORDER:
        if category in chart:
            ok, fail = chart[category]["ok"], chart[category]["fail"]
            total = ok + fail
            chart_rows.append({
                "category": category, "ok": ok, "fail": fail, "total": total,
                "ok_pct": round(ok / total * 100) if total else 0,
                "fail_pct": round(fail / total * 100) if total else 0,
            })

    # Detalle de líneas (header/footer completos, body como muestra)
    line_sections = []
    if parsed is not None:
        for section in ("header", "body", "footer"):
            df = parsed.sections.get(section)
            if df is None or section not in sections:
                continue
            failed = _failed_indices(sections[section])
            limit = MAX_BODY_SAMPLE if section == "body" else len(df)
            rows = []
            for i, (_, row) in enumerate(df.head(limit).iterrows()):
                rows.append({
                    "n": i + 1,
                    "failed": i in failed,
                    "cells": [str(v) for v in row.tolist()],
                })
            line_sections.append({
                "section": section.upper(),
                "columns": list(df.columns),
                "rows": rows,
                "total": int(len(df)),
                "failed": len(failed),
                "passed": int(len(df)) - len(failed),
                "sampled": len(df) > limit,
            })

    return {
        "meta": meta,
        "interface": document.get("interface"),
        "interface_date": document.get("interface_date"),
        "record_count": document.get("record_count", 0),
        "total_expectations": summary.get("total_expectations", 0),
        "success_percent": summary.get("success_percent", 0.0),
        "approved": summary.get("success", False),
        "success_rows": success_rows,
        "error_rows": error_rows,
        "failed_details": failed_details,
        "chart_rows": chart_rows,
        "line_sections": line_sections,
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


# --------------------------------------------------------------------------- #
# Plantilla HTML
# --------------------------------------------------------------------------- #
_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe de Validación - {{ interface }}</title>
<style>{{ css }}
  .lines-table th{ text-transform:none; font-size:8pt; }
  .lines-table td{ font-size:8pt; }
  .passed-line td{ background:#f0fdf4 !important; }
  .failed-line td{ background:#fef2f2 !important; }
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="org">{{ meta.organization }}</div>
    <h1>INFORME DE VALIDACIÓN DE INTERFACES</h1>
    <div class="sub">{{ interface }} · {{ interface_date }}
      <span class="chip">v1.0</span><span class="chip">Evidencia · vigencia 30 días</span></div>
  </div>

  <div class="hero">
    <div class="donut" style="--pct:{{ success_percent }}; --dcol:{{ '#15a34a' if approved else '#dc2626' }};">
      <div class="hole"><b>{{ success_percent }}%</b><small>aprobación</small></div>
    </div>
    <div class="card kpi"><div class="value">{{ record_count }}</div><div class="label">Registros</div></div>
    <div class="card kpi"><div class="value">{{ total_expectations }}</div><div class="label">Expectativas</div></div>
    <div class="card kpi">
      <div class="value">{% if approved %}<span class="pill pill-ok">APROBADO</span>{% else %}<span class="pill pill-bad">RECHAZADO</span>{% endif %}</div>
      <div class="label">Estado · {{ meta.system }}</div>
    </div>
  </div>

  <div class="metastrip">
    <div class="m"><b>Ambiente</b>{{ meta.environment }}</div>
    <div class="m"><b>Fecha emisión</b>{{ generated_at }}</div>
    <div class="m"><b>Fecha interfaz</b>{{ interface_date }}</div>
    <div class="m"><b>Responsable</b>{{ meta.responsible }}</div>
    <div class="m"><b>Certificación</b>{{ meta.certification_type }}</div>
    <div class="m"><b>Proyecto</b>{{ meta.project }}</div>
  </div>

  <div class="section-title">VALIDACIONES EXITOSAS POR CATEGORÍA</div>
  <table>
    <thead><tr><th>Categoría</th><th>Validación</th><th>Ejecuciones</th></tr></thead>
    <tbody>
    {% for row in success_rows %}
    <tr><td><b>{{ row.category }}</b></td><td>{{ row.subtype }}</td><td class="center">{{ row.count }}</td></tr>
    {% endfor %}
    </tbody>
  </table>

  <div class="section-title">Resumen gráfico por categoría</div>
  <div class="card">
    {% for c in chart_rows %}
    <div class="bar-row">
      <div class="bar-label">{{ c.category }}</div>
      <div class="bar">
        <div class="seg-ok" style="width: {{ c.ok_pct }}%"></div>
        <div class="seg-bad" style="width: {{ c.fail_pct }}%"></div>
      </div>
      <div class="bar-count">{{ c.ok }} OK · {{ c.fail }} ✗</div>
    </div>
    {% endfor %}
  </div>

  <div class="section-title">Clasificación por tipo de error</div>
  {% if error_rows %}
  <table>
    <thead><tr><th>Categoría</th><th>Validación</th><th>Ocurrencias</th><th>% del total</th><th>Datos afectados</th></tr></thead>
    <tbody>
    {% for row in error_rows %}
    <tr><td><b>{{ row.category }}</b></td><td>{{ row.subtype }}</td><td class="center">{{ row.count }}</td>
        <td class="center">{{ row.pct }}%</td><td class="center">{{ row.affected }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="note ok-text">✓ No se detectaron errores. La interfaz cumple todas las expectativas.</div>
  {% endif %}

  {% if failed_details %}
  <div class="section-title">Detalle de expectativas fallidas</div>
  <table>
    <thead><tr><th>Validación</th><th>Columna</th><th>Valor esperado</th>
        <th>Valor(es) encontrado(s)</th><th>Línea(s)</th><th>Sección</th><th>Afectados</th></tr></thead>
    <tbody>
    {% for d in failed_details %}
    <tr><td>{{ d.subtype }}</td><td>{{ d.column }}</td><td>{{ d.expected }}</td>
        <td class="found">{{ d.found }}</td>
        <td class="center">{{ d.lines }}</td>
        <td class="center">{{ d.section }}</td><td class="center">{{ d.errors }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
  <p class="muted">«Valor(es) encontrado(s)» y «Línea(s)» muestran hasta 8 ejemplos del dato exacto que provocó el rechazo.</p>
  {% endif %}

  {% for ls in line_sections %}
  <div class="section-title">Detalle de líneas · {{ ls.section }}</div>
  <div class="note">
    Total de líneas: <b>{{ ls.total }}</b> ·
    <span class="ok-text">correctas: {{ ls.passed }}</span> ·
    <span style="color:#dc2626">con observación: {{ ls.failed }}</span>
    {% if ls.sampled %} · <span class="muted">(muestra de las primeras {{ ls.rows|length }})</span>{% endif %}
  </div>
  <div style="overflow-x:auto;">
  <table class="lines-table">
    <thead><tr><th>Nº</th>{% for c in ls.columns %}<th>{{ c }}</th>{% endfor %}</tr></thead>
    <tbody>
    {% for r in ls.rows %}
    <tr class="{{ 'failed-line' if r.failed else 'passed-line' }}">
      <td>{{ r.n }}</td>{% for v in r.cells %}<td>{{ v[:40] }}</td>{% endfor %}
    </tr>
    {% endfor %}
    </tbody>
  </table>
  </div>
  {% endfor %}

  <p class="muted" style="margin-top:24px; text-align:center;">
    Generado automáticamente por gx-interface-validator · {{ generated_at }} · Datos de ejemplo ficticios.
  </p>

</div>
</body>
</html>""")


DEFAULT_META = {
    "organization": "Área de Calidad de Datos",
    "system": "DEMO",
    "environment": "QA",
    "responsible": "Equipo QA",
    "certification_type": "PROYECTO",
    "project": "Proyecto de demostración - Validación de interfaces",
}


def render_html(document: dict, meta: dict | None = None, parsed=None) -> str:
    full_meta = {**DEFAULT_META, **(meta or {})}
    model = build_model(document, full_meta, parsed=parsed)
    return _TEMPLATE.render(css=REPORT_CSS, **model)


def generate_report(
    document: dict,
    output_dir: str | Path,
    meta: dict | None = None,
    parsed=None,
    fmt: str = "html",
) -> dict[str, Path]:
    """
    Genera el informe de usuario.

    Returns:
        dict con las rutas generadas, p. ej. {"html": Path, "pdf": Path}.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base = f"Informe_{document['interface']}_{document['interface_date']}"
    html = render_html(document, meta=meta, parsed=parsed)

    outputs: dict[str, Path] = {}
    html_path = output_dir / f"{base}.html"
    html_path.write_text(html, encoding="utf-8")
    outputs["html"] = html_path

    if fmt in ("pdf", "both"):
        from .pdf import html_to_pdf  # import perezoso

        pdf_path = output_dir / f"{base}.pdf"
        ok, info = html_to_pdf(html, pdf_path)
        if ok:
            outputs["pdf"] = pdf_path
            outputs["pdf_backend"] = info
        else:
            outputs["pdf_error"] = info

    return outputs
