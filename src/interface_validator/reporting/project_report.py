"""
Informe consolidado POR PROYECTO (desde la base de datos).

Agrega las validaciones y comparaciones persistidas de un proyecto en un único
documento (HTML + PDF) con:
  - KPIs (interfaces validadas/comparadas, % de éxito)
  - análisis de expectativas fallidas y de errores de comparación
  - detalle por interfaz con **enlace** a su informe ejecutivo (modo híbrido) y,
    opcionalmente, el informe ejecutivo **embebido** (--embed)
  - enlaces a Metabase (interactivo) y Allure (ejecuciones QA)

Usa el último run por interfaz (estado actual del proyecto).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Template

from .. import config
from .html_report import render_html
from .pdf import html_to_pdf
from .styles import REPORT_CSS


# --------------------------------------------------------------------------- #
# Acceso a datos
# --------------------------------------------------------------------------- #
def _query(conn, sql: str, params: dict | None = None) -> list[dict]:
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()


def _project(conn, project: str) -> dict | None:
    rows = _query(conn,
        "SELECT project_id, project_key, name FROM dim_project WHERE project_key=%(p)s OR name=%(p)s LIMIT 1",
        {"p": project})
    return rows[0] if rows else None


# Último run por interfaz (validaciones)
_LATEST_RUNS = """
SELECT DISTINCT ON (r.interface_id)
       r.run_id, i.name AS interface, r.file_name, r.interface_date,
       r.success, r.success_percent, r.total_expectations, r.successful, r.failed,
       r.duration_ms
FROM fact_run r
JOIN dim_interface i ON i.interface_id = r.interface_id
WHERE r.project_id = %(pid)s
ORDER BY r.interface_id, r.started_at DESC NULLS LAST, r.run_id DESC
"""

# Último comparison run por interfaz
_LATEST_COMPARISONS = """
SELECT DISTINCT ON (c.interface_id)
       c.comparison_run_id, i.name AS interface, c.mode, c.key_columns,
       c.file_a, c.file_b, c.match_percent, c.only_in_a, c.only_in_b, c.differing
FROM fact_comparison_run c
JOIN dim_interface i ON i.interface_id = c.interface_id
WHERE c.project_id = %(pid)s
ORDER BY c.interface_id, c.started_at DESC NULLS LAST, c.comparison_run_id DESC
"""


def _reconstruct_document(conn, run_row: dict) -> dict:
    """Rearma el documento consolidado de una interfaz a partir de la BD."""
    sections_rows = _query(conn,
        "SELECT section_id, section, suite_name, success, evaluated, successful, unsuccessful, success_percent "
        "FROM fact_section WHERE run_id=%(rid)s", {"rid": run_row["run_id"]})

    sections: dict[str, dict] = {}
    for s in sections_rows:
        results = _query(conn,
            "SELECT expectation_type, column_name, success, kwargs, result "
            "FROM fact_expectation WHERE section_id=%(sid)s", {"sid": s["section_id"]})
        sections[s["section"]] = {
            "section": s["section"], "suite": s["suite_name"], "success": s["success"],
            "statistics": {
                "evaluated_expectations": s["evaluated"], "successful_expectations": s["successful"],
                "unsuccessful_expectations": s["unsuccessful"], "success_percent": s["success_percent"],
            },
            "results": [{
                "expectation_type": r["expectation_type"],
                "kwargs": r["kwargs"] or {},
                "success": r["success"],
                "result": r["result"] or {},
            } for r in results],
        }

    return {
        "interface": run_row["interface"],
        "file": run_row["file_name"],
        "interface_date": run_row["interface_date"],
        "summary": {
            "total_expectations": run_row["total_expectations"], "successful": run_row["successful"],
            "failed": run_row["failed"], "success_percent": run_row["success_percent"],
            "success": run_row["success"],
        },
        "sections": sections,
    }


# --------------------------------------------------------------------------- #
# Modelo del informe
# --------------------------------------------------------------------------- #
def build_model(conn, project: str, meta: dict | None = None, embed: bool = False) -> dict:
    proj = _project(conn, project)
    if proj is None:
        raise ValueError(f"El proyecto '{project}' no existe en el catálogo.")
    pid = proj["project_id"]

    validated = _query(conn, _LATEST_RUNS, {"pid": pid})
    compared = _query(conn, _LATEST_COMPARISONS, {"pid": pid})
    run_ids = [v["run_id"] for v in validated] or [-1]

    # Análisis de expectativas fallidas (sobre los últimos runs)
    failed_expectations = _query(conn, """
        SELECT e.category, e.expectation_type, e.column_name,
               COUNT(*) AS fallos,
               COUNT(DISTINCT r.interface_id) AS interfaces_afectadas,
               array_agg(DISTINCT s.section) AS secciones
        FROM fact_expectation e
        JOIN fact_section s ON s.section_id = e.section_id
        JOIN fact_run r ON r.run_id = s.run_id
        WHERE e.success = FALSE AND s.run_id = ANY(%(ids)s)
        GROUP BY e.category, e.expectation_type, e.column_name
        ORDER BY fallos DESC
    """, {"ids": run_ids})
    total_fallos = sum(f["fallos"] for f in failed_expectations) or 1
    for f in failed_expectations:
        f["pct"] = round(f["fallos"] / total_fallos * 100, 1)
        f["secciones"] = ", ".join(x for x in (f["secciones"] or []) if x)

    # Análisis de errores de comparación (todas las comparaciones del proyecto)
    comparison_errors = _query(conn, """
        SELECT d.discrepancy_type,
               COUNT(*) AS ocurrencias,
               COUNT(DISTINCT c.interface_id) AS interfaces
        FROM fact_comparison_diff d
        JOIN fact_comparison_section cs ON cs.comparison_section_id = d.comparison_section_id
        JOIN fact_comparison_run c ON c.comparison_run_id = cs.comparison_run_id
        WHERE c.project_id = %(pid)s
        GROUP BY d.discrepancy_type
        ORDER BY ocurrencias DESC
    """, {"pid": pid})
    total_cmp_err = sum(c["ocurrencias"] for c in comparison_errors) or 1
    for c in comparison_errors:
        c["pct"] = round(c["ocurrencias"] / total_cmp_err * 100, 1)

    # KPIs
    n_val = len(validated)
    n_val_ok = sum(1 for v in validated if v["success"])
    n_cmp = len(compared)
    n_cmp_ok = sum(1 for c in compared if (c["only_in_a"] or 0) + (c["only_in_b"] or 0) + (c["differing"] or 0) == 0)

    # Drill-down embebido (--embed): detalle de fallos por interfaz, inline.
    if embed:
        for v in validated:
            v["failed_details"] = _query(conn, """
                SELECT e.category, e.column_name, e.expected_text, e.found_examples,
                       e.affected_lines, s.section
                FROM fact_expectation e
                JOIN fact_section s ON s.section_id = e.section_id
                WHERE s.run_id = %(rid)s AND e.success = FALSE
                ORDER BY s.section
            """, {"rid": v["run_id"]})

    return {
        "project": proj, "meta": meta or {},
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "kpis": {
            "interfaces_validadas": n_val, "validadas_ok": n_val_ok,
            "pct_exito_validacion": round(n_val_ok / n_val * 100, 1) if n_val else 0.0,
            "interfaces_comparadas": n_cmp, "comparadas_ok": n_cmp_ok,
            "pct_exito_comparacion": round(n_cmp_ok / n_cmp * 100, 1) if n_cmp else 0.0,
        },
        "failed_expectations": failed_expectations,
        "comparison_errors": comparison_errors,
        "validated": validated,
        "compared": compared,
        "embed": embed,
        "metabase_url": config.METABASE_URL,
        "allure_url": config.ALLURE_URL,
    }


# --------------------------------------------------------------------------- #
# Plantilla y render
# --------------------------------------------------------------------------- #
_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe de Proyecto — {{ project.project_key }}</title>
<style>{{ css }}
  .embed-block{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:10px 14px; margin:10px 0; }
  .embed-block h4{ margin:4px 0 8px; color:var(--primary-dark); }
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="org">{{ meta.organization or 'Área de Calidad de Datos' }}</div>
    <h1>INFORME CONSOLIDADO DE INTERFACES</h1>
    <div class="sub">{{ project.name }} · {{ project.project_key }}
      <span class="chip">{{ generated_at }}</span></div>
  </div>

  <div class="section-title">Resumen General</div>
  <div class="hero">
    <div class="donut" style="--pct:{{ kpis.pct_exito_validacion }}; --dcol:{{ '#15a34a' if kpis.pct_exito_validacion >= 100 else '#d97706' if kpis.pct_exito_validacion >= 50 else '#dc2626' }};">
      <div class="hole"><b>{{ kpis.pct_exito_validacion }}%</b><small>validación</small></div>
    </div>
    <div class="donut" style="--pct:{{ kpis.pct_exito_comparacion }}; --dcol:{{ '#15a34a' if kpis.pct_exito_comparacion >= 100 else '#d97706' if kpis.pct_exito_comparacion >= 50 else '#dc2626' }};">
      <div class="hole"><b>{{ kpis.pct_exito_comparacion }}%</b><small>comparación</small></div>
    </div>
    <div class="card kpi"><div class="value">{{ kpis.interfaces_validadas }}</div><div class="label">Interfaces validadas ({{ kpis.validadas_ok }} OK)</div></div>
    <div class="card kpi"><div class="value">{{ kpis.interfaces_comparadas }}</div><div class="label">Interfaces comparadas ({{ kpis.comparadas_ok }} OK)</div></div>
  </div>

  <div class="section-title">Análisis de Expectativas Fallidas</div>
  {% if failed_expectations %}
  <table>
    <thead><tr><th>Expectativa</th><th>Categoría</th><th>Secciones</th><th>Cant. Fallos</th><th>%</th><th>Interfaces afectadas</th></tr></thead>
    <tbody>
    {% for f in failed_expectations %}
    <tr><td>{{ f.expectation_type }}{% if f.column_name %} <span class="muted">[{{ f.column_name }}]</span>{% endif %}</td>
        <td><b>{{ f.category }}</b></td><td>{{ f.secciones }}</td>
        <td class="center">{{ f.fallos }}</td><td class="center">{{ f.pct }}%</td>
        <td class="center">{{ f.interfaces_afectadas }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<div class="note ok-text">✓ Sin expectativas fallidas en el proyecto.</div>{% endif %}

  <div class="section-title">Análisis de Errores de Comparación</div>
  {% if comparison_errors %}
  <table>
    <thead><tr><th>Tipo de Error</th><th>Ocurrencias</th><th>Interfaces</th><th>% del Total</th></tr></thead>
    <tbody>
    {% for c in comparison_errors %}
    <tr><td>{{ c.discrepancy_type }}</td><td class="center">{{ c.ocurrencias }}</td>
        <td class="center">{{ c.interfaces }}</td><td class="center">{{ c.pct }}%</td></tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="muted">Sin comparaciones registradas para este proyecto.</p>{% endif %}

  <div class="section-title">Detalle de Interfaces Validadas</div>
  <table>
    <thead><tr><th>Interfaz</th><th>Fecha</th><th>Evaluadas</th><th>Exitosas</th><th>Fallidas</th><th>Tasa</th><th>Estado</th><th>Detalle</th></tr></thead>
    <tbody>
    {% for v in validated %}
    <tr><td><b>{{ v.interface }}</b></td><td class="center">{{ v.interface_date }}</td>
        <td class="center">{{ v.total_expectations }}</td><td class="center">{{ v.successful }}</td>
        <td class="center">{{ v.failed }}</td><td class="center">{{ v.success_percent }}%</td>
        <td class="center"><span class="pill {{ 'pill-ok' if v.success else 'pill-bad' }}">{{ 'APROBADO' if v.success else 'RECHAZADO' }}</span></td>
        <td class="center">{% if v.report_link %}<a href="{{ v.report_link }}">ver informe →</a>{% else %}-{% endif %}</td></tr>
    {% endfor %}
    </tbody>
  </table>

  {% if embed %}
  {% for v in validated %}{% if v.failed_details %}
  <div class="embed-block">
    <h4>{{ v.interface }} — expectativas fallidas</h4>
    <table>
      <thead><tr><th>Sección</th><th>Categoría</th><th>Columna</th><th>Valor esperado</th><th>Encontrado</th><th>Líneas</th></tr></thead>
      <tbody>
      {% for d in v.failed_details %}
      <tr><td class="center">{{ d.section }}</td><td>{{ d.category }}</td><td>{{ d.column_name }}</td>
          <td>{{ d.expected_text }}</td><td class="found">{{ d.found_examples }}</td>
          <td class="center">{{ d.affected_lines }}</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}{% endfor %}
  {% endif %}

  <div class="section-title">Detalle de Interfaces Comparadas</div>
  {% if compared %}
  <table>
    <thead><tr><th>Interfaz</th><th>Modo</th><th>Archivos</th><th>Coincidencia</th><th>Solo A</th><th>Solo B</th><th>Difieren</th></tr></thead>
    <tbody>
    {% for c in compared %}
    <tr><td><b>{{ c.interface }}</b></td><td class="center">{{ c.mode }}</td>
        <td class="muted">{{ c.file_a }} vs {{ c.file_b }}</td><td class="center">{{ c.match_percent }}%</td>
        <td class="center">{{ c.only_in_a }}</td><td class="center">{{ c.only_in_b }}</td>
        <td class="center">{{ c.differing }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="muted">Sin comparaciones registradas.</p>{% endif %}

  <div class="linkbar">
    🔗 Vistas complementarias:
    <a href="{{ metabase_url }}">Dashboard interactivo (Metabase)</a> ·
    <a href="{{ allure_url }}">Reporte de pruebas QA (Allure)</a>
  </div>

  <p class="muted" style="text-align:center; margin-top:22px;">Generado automáticamente por gx-interface-validator · {{ generated_at }} · Datos de ejemplo ficticios.</p>
</div>
</body>
</html>""")


def render_project_html(model: dict) -> str:
    return _TEMPLATE.render(css=REPORT_CSS, **model)


def generate_project_report(conn, project: str, output_dir, meta: dict | None = None,
                            fmt: str = "html", embed: bool = False) -> dict:
    """Genera el informe consolidado del proyecto (HTML/PDF) + los informes por interfaz."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model = build_model(conn, project, meta=meta, embed=embed)

    # Drill-down enlazado: informe ejecutivo por interfaz (reconstruido de la BD)
    for v in model["validated"]:
        run_row = next(r for r in _query(conn, _LATEST_RUNS, {"pid": model["project"]["project_id"]})
                       if r["run_id"] == v["run_id"])
        doc = _reconstruct_document(conn, run_row)
        link_name = f"Informe_{v['interface']}.html"
        (output_dir / link_name).write_text(render_html(doc, meta=meta, parsed=None), encoding="utf-8")
        v["report_link"] = link_name

    key = model["project"]["project_key"]
    html = render_project_html(model)
    outputs: dict = {}
    html_path = output_dir / f"Informe_Proyecto_{key}.html"
    html_path.write_text(html, encoding="utf-8")
    outputs["html"] = html_path

    if fmt in ("pdf", "both"):
        pdf_path = output_dir / f"Informe_Proyecto_{key}.pdf"
        ok, info = html_to_pdf(html, pdf_path)
        if ok:
            outputs["pdf"] = pdf_path
        else:
            outputs["pdf_error"] = info

    outputs["model"] = model
    return outputs
