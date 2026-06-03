"""
CLI de comparación de interfaces.

Compara dos versiones/archivos de la misma interfaz, por línea o por ID:

    compare-interfaces --file-a A.FC --file-b B.FC --layout sample01 --mode by_id
    compare-interfaces --file-a A.FC --file-b B.FC --mode by_line
    compare-interfaces ... --mode by_id --keys ENTRY_ID --project RIESGO --user dleiva --persist

Genera un JSON de comparación y, opcionalmente, lo persiste en PostgreSQL.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .comparison import compare_interfaces


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compare-interfaces",
        description="Compara dos versiones de una interfaz (por línea o por ID).",
    )
    parser.add_argument("--file-a", "-a", required=True, help="Archivo A (versión original).")
    parser.add_argument("--file-b", "-b", required=True, help="Archivo B (versión a comparar).")
    parser.add_argument("--layout", "-l", default="sample01", help="Nombre del layout (FD).")
    parser.add_argument("--mode", choices=["by_id", "by_line"], default="by_id",
                        help="by_id (por columnas clave, por sección) o by_line (línea a línea).")
    parser.add_argument("--keys", default=None,
                        help="Columnas clave para by_id (separadas por coma). Sobreescribe el layout.")
    parser.add_argument("--output", "-o", default=None, help="Directorio de salida del JSON.")
    parser.add_argument("--persist", action="store_true",
                        help="Guarda la comparación en PostgreSQL (requiere --project y --user).")
    parser.add_argument("--project", default=None, help="Proyecto (debe existir en el catálogo).")
    parser.add_argument("--user", default=None, help="Usuario (debe existir en el catálogo).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.persist and (not args.project or not args.user):
        print("[ERROR] --persist requiere --project y --user.", file=sys.stderr)
        return 2

    keys = [k.strip() for k in args.keys.split(",")] if args.keys else None
    comparison_run_id = None

    try:
        document = compare_interfaces(
            args.file_a, args.file_b, args.layout, mode=args.mode, key_columns=keys
        )
        out_dir = Path(args.output) if args.output else config.OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"comparacion.{document['interface']}.{document['mode']}.json"
        out_path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")

        if args.persist:
            from .db import CatalogError, load_comparison

            try:
                comparison_run_id = load_comparison(document, project=args.project, user=args.user)
            except CatalogError as exc:
                print(f"[ERROR] {exc}", file=sys.stderr)
                return 2
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    s = document["summary"]
    print(f"Interfaz : {document['interface']}  (modo {document['mode']})")
    print(f"Archivos : {document['file_a']}  vs  {document['file_b']}")
    if document.get("key_columns"):
        print(f"Claves   : {', '.join(document['key_columns'])}")
    print(f"Coincide : {s['match_percent']}%   "
          f"(solo A={s['only_in_a']}, solo B={s['only_in_b']}, difieren={s['differing']})")
    for section, b in document["sections"].items():
        print(f"  [{section:<12}] {b['match_percent']:>6}%  "
              f"soloA={b['only_in_a']} soloB={b['only_in_b']} dif={b['differing']}")
    print(f"Duración : {document['duration_ms']} ms")
    print(f"JSON     : {out_path}")
    if comparison_run_id is not None:
        print(f"BD       : guardado con comparison_run_id={comparison_run_id} "
              f"(proyecto '{args.project}', usuario '{args.user}')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
