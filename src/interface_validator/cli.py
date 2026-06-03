"""
CLI del validador de interfaces.

Permite a un QA automatizador validar una interfaz sin levantar ninguna UI:

    validate-interface --file data/sample/SAMPLE01_F20250404.FC
    validate-interface --file ... --layout sample01 --report both

Genera el JSON consolidado y, opcionalmente, el informe de cara al usuario
(HTML/PDF). Código de salida:
    0 = todas las expectativas pasaron
    1 = hubo al menos una expectativa fallida
    2 = error de ejecución
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config
from .consolidator import write_consolidated
from .reporting import generate_report
from .service import parse_and_validate


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate-interface",
        description="Valida una interfaz de ancho fijo con Great Expectations.",
    )
    parser.add_argument("--file", "-f", required=True, help="Ruta al archivo .FC a validar.")
    parser.add_argument("--layout", "-l", default="sample01", help="Nombre del layout (FD).")
    parser.add_argument("--expectations", "-e", default=None, help="Directorio de suites de expectativas.")
    parser.add_argument("--output", "-o", default=None, help="Directorio de salida.")
    parser.add_argument("--report", choices=["none", "html", "pdf", "both"], default="none",
                        help="Generar informe de usuario además del JSON.")
    # Metadatos del informe
    parser.add_argument("--system", default=None, help="Sistema / área dueña de la interfaz.")
    parser.add_argument("--responsible", default=None, help="Responsable del proyecto.")
    parser.add_argument("--project", default=None, help="Proyecto asociado (project_key o nombre).")
    parser.add_argument("--environment", default=None, help="Ambiente (QA, PROD, ...).")
    # Persistencia en base de datos
    parser.add_argument("--persist", action="store_true",
                        help="Guarda los resultados en PostgreSQL (requiere --project y --user).")
    parser.add_argument("--user", default=None, help="Usuario que ejecuta la validación (debe existir en el catálogo).")
    return parser


def _meta_from_args(args) -> dict:
    meta = {}
    if args.system:
        meta["system"] = args.system
    if args.responsible:
        meta["responsible"] = args.responsible
    if args.project:
        meta["project"] = args.project
    if args.environment:
        meta["environment"] = args.environment
    return meta


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_dir = Path(args.output) if args.output else config.OUTPUT_DIR
    expectations_dir = Path(args.expectations) if args.expectations else config.EXPECTATIONS_DIR

    if args.persist and (not args.project or not args.user):
        print("[ERROR] --persist requiere --project y --user.", file=sys.stderr)
        return 2

    run_id = None
    try:
        parsed, document = parse_and_validate(args.file, args.layout, expectations_dir)
        out_path = write_consolidated(document, output_dir)
        document["_output_path"] = str(out_path)

        report_paths = {}
        if args.report != "none":
            report_paths = generate_report(
                document, output_dir, meta=_meta_from_args(args),
                parsed=parsed, fmt=args.report,
            )

        if args.persist:
            from .db import CatalogError, load_document

            try:
                run_id = load_document(document, project=args.project, user=args.user)
            except CatalogError as exc:
                print(f"[ERROR] {exc}", file=sys.stderr)
                return 2
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    summary = document["summary"]
    status = "OK" if summary["success"] else "FALLIDO"
    print(f"Interfaz : {document['interface']}  ({document['file']})")
    print(f"Fecha    : {document['interface_date']}")
    print(f"Resultado: {status}  -  {summary['successful']}/{summary['total_expectations']} "
          f"expectativas ({summary['success_percent']}%)")
    for section, block in document["sections"].items():
        st = block["statistics"]
        mark = "OK " if block["success"] else "XX "
        print(f"  [{mark}] {section:<14} {st['successful_expectations']}/{st['evaluated_expectations']}")
    print(f"Duración : {document.get('duration_ms', '?')} ms")
    print(f"JSON     : {document.get('_output_path', '(no escrito)')}")
    if run_id is not None:
        print(f"BD       : guardado con run_id={run_id} (proyecto '{args.project}', usuario '{args.user}')")
    if report_paths.get("html"):
        print(f"Informe  : {report_paths['html']}")
    if report_paths.get("pdf"):
        print(f"PDF      : {report_paths['pdf']}")
    elif report_paths.get("pdf_error"):
        print(f"PDF      : no generado ({report_paths['pdf_error']}). Abra el HTML e imprima a PDF.")

    return 0 if summary["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
