"""
CLI del informe consolidado por proyecto (desde la base de datos).

    project-report --project RIESGO --format both
    project-report --project RIESGO --embed          # versión "todo-en-uno"

Genera el informe del proyecto (HTML/PDF) y un informe ejecutivo por interfaz
enlazado. Requiere la BD con resultados persistidos.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config
from .db.connection import get_connection
from .reporting.project_report import generate_project_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-report",
        description="Informe consolidado de un proyecto (validaciones + comparaciones).",
    )
    parser.add_argument("--project", required=True, help="project_key o nombre del proyecto.")
    parser.add_argument("--format", choices=["html", "pdf", "both"], default="both")
    parser.add_argument("--embed", action="store_true",
                        help="Incluye el detalle por interfaz embebido (un solo documento).")
    parser.add_argument("--output", "-o", default=None, help="Directorio de salida.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out_dir = Path(args.output) if args.output else config.OUTPUT_DIR

    try:
        conn = get_connection()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] No se pudo conectar a la base de datos: {exc}", file=sys.stderr)
        return 2

    try:
        outputs = generate_project_report(
            conn, args.project, out_dir, fmt=args.format, embed=args.embed
        )
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()

    m = outputs["model"]
    k = m["kpis"]
    print(f"Proyecto : {m['project']['project_key']} — {m['project']['name']}")
    print(f"Validadas: {k['interfaces_validadas']} ({k['pct_exito_validacion']}% éxito)  ·  "
          f"Comparadas: {k['interfaces_comparadas']} ({k['pct_exito_comparacion']}% éxito)")
    print(f"HTML     : {outputs['html']}")
    if outputs.get("pdf"):
        print(f"PDF      : {outputs['pdf']}")
    elif outputs.get("pdf_error"):
        print(f"PDF      : no generado ({outputs['pdf_error']})")
    print(f"(informes por interfaz enlazados en {out_dir})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
