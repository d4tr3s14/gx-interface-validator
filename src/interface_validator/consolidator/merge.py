"""
Consolidación de resultados.

El proyecto original generaba TRES JSON por interfaz (header, body, footer).
Aquí se unifican en UN SOLO JSON por interfaz, con un resumen global y el
detalle por sección, más las reglas de negocio cross-section.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _aggregate_stats(section_blocks: list[dict]) -> dict:
    total = sum(b["statistics"]["evaluated_expectations"] for b in section_blocks)
    ok = sum(b["statistics"]["successful_expectations"] for b in section_blocks)
    return {
        "total_expectations": total,
        "successful": ok,
        "failed": total - ok,
        "success_percent": round(ok / total * 100, 2) if total else 100.0,
        "success": all(b["success"] for b in section_blocks) if section_blocks else True,
    }


def consolidate(
    interface: str,
    file_name: str,
    interface_date: str,
    section_blocks: dict[str, dict],
) -> dict:
    """
    Une los bloques de resultado por sección en un único documento.

    Args:
        interface: nombre lógico de la interfaz (p. ej. "SAMPLE01").
        file_name: nombre del archivo validado.
        interface_date: fecha de la interfaz (YYYYMMDD).
        section_blocks: dict {seccion -> bloque normalizado del runner}.
    """
    blocks = list(section_blocks.values())
    return {
        "interface": interface,
        "file": file_name,
        "interface_date": interface_date,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "summary": _aggregate_stats(blocks),
        "sections": section_blocks,
    }


def write_consolidated(document: dict, output_dir: str | Path) -> Path:
    """Escribe el JSON consolidado y devuelve la ruta del archivo."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"resultado.{document['interface']}.{document['interface_date']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)
    return out_path
