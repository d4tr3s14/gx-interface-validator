"""
Orquestador de alto nivel: de un archivo `.FC` a un JSON consolidado.

Encadena las cuatro etapas del pipeline:
    parser  ->  motor GE (por sección)  ->  reglas cross-section  ->  consolidador

Es el punto de entrada que usan tanto el CLI como los step definitions de BDD.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config
from .consolidator import consolidate, write_consolidated
from .engine import run_section
from .engine.cross_section import run_cross_section
from .parser import FixedWidthParser, ParsedInterface, load_layout

_DATE_RE = re.compile(r"_F(\d{8})")


def extract_date(file_name: str) -> str:
    """Extrae la fecha YYYYMMDD del nombre de archivo (patrón `_FYYYYMMDD`)."""
    match = _DATE_RE.search(file_name)
    return match.group(1) if match else "00000000"


def load_suite(interface: str, section: str, expectations_dir: Path | None = None) -> tuple[str, list[dict]]:
    """Carga la suite de expectativas `<interface>_<section>.json`."""
    expectations_dir = Path(expectations_dir or config.EXPECTATIONS_DIR)
    path = expectations_dir / f"{interface.lower()}_{section}.json"
    if not path.exists():
        return f"{interface}_{section}", []
    with open(path, "r", encoding="utf-8") as f:
        suite = json.load(f)
    return suite.get("suite_name", path.stem), suite.get("expectations", [])


def validate_parsed(
    parsed: ParsedInterface,
    interface_date: str,
    expectations_dir: Path | None = None,
    business_rules: list[dict] | None = None,
) -> dict:
    """Valida una interfaz ya parseada y devuelve el documento consolidado."""
    section_blocks: dict[str, dict] = {}
    row_counts: dict[str, int] = {}

    for section in ("header", "body", "footer"):
        df = parsed.sections.get(section)
        if df is None:
            continue
        row_counts[section] = int(len(df))
        suite_name, entries = load_suite(parsed.interface, section, expectations_dir)
        section_blocks[section] = run_section(df, entries, section, suite_name)

    # Reglas de negocio que cruzan secciones (footer vs. body)
    section_blocks["cross_section"] = run_cross_section(parsed.sections, business_rules)

    document = consolidate(
        interface=parsed.interface,
        file_name=parsed.file_name,
        interface_date=interface_date,
        section_blocks=section_blocks,
    )
    document["row_counts"] = row_counts
    document["record_count"] = row_counts.get("body", 0)
    return document


def parse_and_validate(
    fc_path: str | Path,
    layout_name: str = "sample01",
    expectations_dir: Path | None = None,
) -> tuple[ParsedInterface, dict]:
    """Parsea y valida una interfaz; devuelve (parsed, documento_consolidado)."""
    fc_path = Path(fc_path)
    layout = load_layout(layout_name)
    parsed = FixedWidthParser(layout).parse_file(fc_path)
    document = validate_parsed(
        parsed,
        interface_date=extract_date(fc_path.name),
        expectations_dir=expectations_dir,
        business_rules=layout.get("business_rules", []),
    )
    return parsed, document


def validate_interface(
    fc_path: str | Path,
    layout_name: str = "sample01",
    expectations_dir: Path | None = None,
    output_dir: Path | None = None,
    write: bool = True,
) -> dict:
    """
    Valida una interfaz completa desde su archivo `.FC`.

    Returns:
        El documento consolidado (un único JSON por interfaz).
    """
    _, document = parse_and_validate(fc_path, layout_name, expectations_dir)

    if write:
        out_path = write_consolidated(document, output_dir or config.OUTPUT_DIR)
        document["_output_path"] = str(out_path)

    return document
