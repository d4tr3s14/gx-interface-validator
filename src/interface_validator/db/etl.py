"""
ETL: carga un documento consolidado de validación en PostgreSQL.

Flujo:
  1. Verifica el catálogo: el proyecto y el usuario DEBEN existir (si no, error).
  2. Da de alta la interfaz y el puente proyecto-interfaz.
  3. Inserta la ejecución (run), sus secciones y sus expectativas.

Todo ocurre en una transacción: o se carga todo, o no se carga nada.
"""
from __future__ import annotations

from ..reporting import taxonomy
from .connection import get_connection
from . import repository as repo


class CatalogError(Exception):
    """El proyecto o el usuario no existen en el catálogo gestionado."""


def _expectation_fields(section: str, result: dict) -> dict:
    category, _ = taxonomy.categorize(result["expectation_type"], section)
    examples = taxonomy.error_examples(result) if not result.get("success") else {"found": "", "lines": ""}
    return {
        "expectation_type": result.get("expectation_type"),
        "category": category,
        "column_name": result.get("kwargs", {}).get("column"),
        "success": bool(result.get("success", False)),
        "expected_text": taxonomy.expected_text(result),
        "found_examples": examples["found"] or None,
        "affected_lines": examples["lines"] or None,
        "unexpected_count": taxonomy.error_count(result),
        "kwargs": result.get("kwargs", {}),
        "result": result.get("result", {}),
    }


def load_document(document: dict, project: str, user: str, conn=None) -> int:
    """
    Persiste un documento consolidado. Devuelve el `run_id` insertado.

    Args:
        document: el JSON consolidado (salida de `service.validate_interface`).
        project: project_key o nombre de un proyecto **existente** en el catálogo.
        user: username de un usuario **existente** en el catálogo.

    Raises:
        CatalogError: si el proyecto o el usuario no existen.
    """
    own_conn = conn is None
    conn = conn or get_connection()
    try:
        project_id = repo.get_project_id(conn, project)
        if project_id is None:
            raise CatalogError(
                f"El proyecto '{project}' no existe en el catálogo (dim_project). "
                f"Debe darse de alta antes de validar."
            )
        user_id = repo.get_user_id(conn, user)
        if user_id is None:
            raise CatalogError(
                f"El usuario '{user}' no existe en el catálogo (dim_user). "
                f"Debe darse de alta antes de validar."
            )

        interface_id = repo.ensure_interface(conn, document["interface"], document.get("layout"))
        repo.ensure_bridge(conn, project_id, interface_id)

        run_id = repo.insert_run(conn, document, interface_id, project_id, user_id)

        row_counts = document.get("row_counts", {})
        for section, block in document.get("sections", {}).items():
            section_id = repo.insert_section(conn, run_id, section, block, row_counts.get(section))
            for result in block.get("results", []):
                repo.insert_expectation(conn, section_id, _expectation_fields(section, result))

        conn.commit()
        return run_id
    except Exception:
        conn.rollback()
        raise
    finally:
        if own_conn:
            conn.close()
