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
<style>
  @page { size: A4; margin: 1.6cm; @bottom-right { content: counter(page) " / " counter(pages); font-size: 9pt; } }
  body { font-family: 'Segoe UI', Calibri, sans-serif; color: #2b2b2b; font-size: 10.5pt; line-height: 1.45; margin: 0; }
  .container { max-width: 200mm; margin: 0 auto; padding: 16px; }
  .header { text-align: center; color: #fff; padding: 18px; border-radius: 6px;
            background: linear-gradient(135deg, #1f3c88, #4F81BD); box-shadow: 0 2px 6px rgba(0,0,0,.15); }
  .header .org { font-size: 9.5pt; opacity: .9; letter-spacing: .5px; }
  .header .title { font-size: 20pt; font-weight: 700; margin: 6px 0; }
  .header .subtitle { display: flex; justify-content: space-between; font-size: 9pt; opacity: .9; }
  table { width: 100%; border-collapse: collapse; margin: 10px 0 18px; font-size: 9.5pt; }
  th { background: #4F81BD; color: #fff; padding: 7px; text-align: center; font-weight: 600; }
  td { padding: 6px 7px; border: 0.5pt solid #d9d9d9; vertical-align: top; }
  .center { text-align: center; }
  .section-header { background: linear-gradient(to right, #1f3c88, #4F81BD); color: #fff;
                    padding: 7px 12px; font-weight: 700; border-radius: 4px; margin: 22px 0 6px; font-size: 11pt; }
  .badge { padding: 3px 12px; border-radius: 12px; font-weight: 700; font-size: 9pt; }
  .badge-ok { color: #1b5e20; background: #E8F5E9; border: 1px solid #1b5e20; }
  .badge-no { color: #b71c1c; background: #FFEBEE; border: 1px solid #b71c1c; }
  .cat-table td:first-child { font-weight: 600; background: #f4f7fb; }
  .chart .bar-row { display: flex; align-items: center; margin: 5px 0; font-size: 9.5pt; }
  .chart .bar-label { width: 110px; font-weight: 600; }
  .chart .bar { flex: 1; height: 18px; background: #eee; border-radius: 9px; overflow: hidden; display: flex; }
  .chart .bar .ok { background: #43a047; height: 100%; }
  .chart .bar .fail { background: #e53935; height: 100%; }
  .chart .bar-count { width: 90px; text-align: right; color: #555; }
  .lines-table { font-size: 8pt; }
  .lines-table th { background: #4F81BD; }
  .passed-line td { background: #E8F5E9; }
  .failed-line td { background: #FFEBEE; }
  .stats { background: #f4f7fb; border-left: 4px solid #4F81BD; padding: 6px 12px; font-size: 9pt; margin: 6px 0; }
  .stats span { margin-right: 18px; }
  .muted { color: #888; font-size: 8.5pt; }
  .ok-text { color: #1b5e20; font-weight: 600; }
  .failed-table .found { font-family: Consolas, monospace; color: #b71c1c; font-size: 8.5pt; word-break: break-word; }
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="org">{{ meta.organization }}</div>
    <div class="title">INFORME DE VALIDACIÓN DE INTERFACES</div>
    <div class="subtitle"><span>Versión 1.0</span><span>Documento de evidencia · Vigencia 30 días</span></div>
  </div>

  <table>
    <tr><th>SISTEMA</th><th>INTERFAZ</th><th>TOTAL REGISTROS</th><th>TOTAL EXPECTATIVAS</th><th>TASA DE APROBACIÓN</th><th>ESTADO</th></tr>
    <tr>
      <td class="center">{{ meta.system }}</td>
      <td class="center">{{ interface }}</td>
      <td class="center">{{ record_count }}</td>
      <td class="center">{{ total_expectations }}</td>
      <td class="center">{{ success_percent }}%</td>
      <td class="center">
        {% if approved %}<span class="badge badge-ok">APROBADO</span>
        {% else %}<span class="badge badge-no">RECHAZADO</span>{% endif %}
      </td>
    </tr>
  </table>

  <table>
    <tr><th>AMBIENTE</th><th>FECHA EMISIÓN</th><th>FECHA INTERFAZ</th><th>RESPONSABLE</th><th>TIPO CERTIFICACIÓN</th><th>INFORME</th></tr>
    <tr>
      <td class="center">{{ meta.environment }}</td>
      <td class="center">{{ generated_at }}</td>
      <td class="center">{{ interface_date }}</td>
      <td class="center">{{ meta.responsible }}</td>
      <td class="center">{{ meta.certification_type }}</td>
      <td class="center">Automático</td>
    </tr>
  </table>

  <table>
    <tr><th colspan="6">PROYECTO ASOCIADO</th></tr>
    <tr><td colspan="6" class="center">{{ meta.project }}</td></tr>
  </table>

  <div class="section-header">VALIDACIONES EXITOSAS POR CATEGORÍA</div>
  <table class="cat-table">
    <tr><th>CATEGORÍA</th><th>VALIDACIÓN</th><th>EJECUCIONES</th></tr>
    {% for row in success_rows %}
    <tr><td>{{ row.category }}</td><td>{{ row.subtype }}</td><td class="center">{{ row.count }}</td></tr>
    {% endfor %}
  </table>

  <div class="section-header">RESUMEN GRÁFICO POR CATEGORÍA</div>
  <div class="chart">
    {% for c in chart_rows %}
    <div class="bar-row">
      <div class="bar-label">{{ c.category }}</div>
      <div class="bar">
        <div class="ok" style="width: {{ c.ok_pct }}%"></div>
        <div class="fail" style="width: {{ c.fail_pct }}%"></div>
      </div>
      <div class="bar-count">{{ c.ok }} OK / {{ c.fail }} ✗</div>
    </div>
    {% endfor %}
  </div>

  <div class="section-header">CLASIFICACIÓN POR TIPO DE ERROR</div>
  {% if error_rows %}
  <table>
    <tr><th>CATEGORÍA</th><th>VALIDACIÓN</th><th>OCURRENCIAS</th><th>% DEL TOTAL</th><th>DATOS AFECTADOS</th></tr>
    {% for row in error_rows %}
    <tr><td>{{ row.category }}</td><td>{{ row.subtype }}</td><td class="center">{{ row.count }}</td>
        <td class="center">{{ row.pct }}%</td><td class="center">{{ row.affected }}</td></tr>
    {% endfor %}
  </table>
  {% else %}
  <p class="ok-text">✓ No se detectaron errores. La interfaz cumple todas las expectativas.</p>
  {% endif %}

  {% if failed_details %}
  <div class="section-header">DETALLE DE EXPECTATIVAS FALLIDAS</div>
  <table class="failed-table">
    <tr><th>VALIDACIÓN</th><th>COLUMNA</th><th>VALOR ESPERADO</th>
        <th>VALOR(ES) ENCONTRADO(S)</th><th>LÍNEA(S)</th><th>SECCIÓN</th><th>AFECTADOS</th></tr>
    {% for d in failed_details %}
    <tr><td>{{ d.subtype }}</td><td>{{ d.column }}</td><td>{{ d.expected }}</td>
        <td class="found">{{ d.found }}</td>
        <td class="center">{{ d.lines }}</td>
        <td class="center">{{ d.section }}</td><td class="center">{{ d.errors }}</td></tr>
    {% endfor %}
  </table>
  <p class="muted">«Valor(es) encontrado(s)» y «Línea(s)» muestran hasta 8 ejemplos del dato exacto que provocó el rechazo.</p>
  {% endif %}

  {% for ls in line_sections %}
  <div class="section-header">DETALLE DE LÍNEAS · {{ ls.section }}</div>
  <div class="stats">
    <span>Total de líneas: <b>{{ ls.total }}</b></span>
    <span class="ok-text">Correctas: {{ ls.passed }}</span>
    <span style="color:#b71c1c">Con observación: {{ ls.failed }}</span>
    {% if ls.sampled %}<span class="muted">(muestra de las primeras {{ ls.rows|length }})</span>{% endif %}
  </div>
  <div style="overflow-x:auto;">
  <table class="lines-table">
    <tr><th>Nº</th>{% for c in ls.columns %}<th>{{ c }}</th>{% endfor %}</tr>
    {% for r in ls.rows %}
    <tr class="{{ 'failed-line' if r.failed else 'passed-line' }}">
      <td>{{ r.n }}</td>{% for v in r.cells %}<td>{{ v[:40] }}</td>{% endfor %}
    </tr>
    {% endfor %}
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
    return _TEMPLATE.render(**model)


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
