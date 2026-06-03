"""
Operaciones de base de datos (sobre una conexión psycopg abierta).

- Lecturas de catálogo (proyecto/usuario): NO crean nada; devuelven id o None.
- `dim_interface` y el puente sí se dan de alta automáticamente.
- Inserciones de hechos (run / section / expectation).
"""
from __future__ import annotations

import json
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Catálogo gestionado (solo lectura): proyecto y usuario deben existir
# --------------------------------------------------------------------------- #
def get_project_id(conn, project: str) -> Optional[int]:
    """Busca por project_key o por nombre. Devuelve el id o None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT project_id FROM dim_project WHERE project_key = %s OR name = %s LIMIT 1",
            (project, project),
        )
        row = cur.fetchone()
        return row[0] if row else None


def get_user_id(conn, username: str) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM dim_user WHERE username = %s", (username,))
        row = cur.fetchone()
        return row[0] if row else None


# --------------------------------------------------------------------------- #
# Alta automática: interfaz y puente proyecto-interfaz
# --------------------------------------------------------------------------- #
def ensure_interface(conn, name: str, layout: Optional[str]) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_interface (name, layout) VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE SET layout = COALESCE(EXCLUDED.layout, dim_interface.layout)
            RETURNING interface_id
            """,
            (name, layout),
        )
        return cur.fetchone()[0]


def ensure_bridge(conn, project_id: int, interface_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO bridge_project_interface (project_id, interface_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
            """,
            (project_id, interface_id),
        )


# --------------------------------------------------------------------------- #
# Inserción de hechos
# --------------------------------------------------------------------------- #
def insert_run(conn, document: dict, interface_id: int, project_id: int, user_id: int) -> int:
    s = document.get("summary", {})
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_run
                (interface_id, project_id, user_id, file_name, interface_date, environment,
                 started_at, finished_at, duration_ms, success,
                 total_expectations, successful, failed, success_percent)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING run_id
            """,
            (
                interface_id, project_id, user_id,
                document.get("file"), document.get("interface_date"), document.get("environment"),
                document.get("started_at"), document.get("finished_at"), document.get("duration_ms"),
                bool(s.get("success", False)),
                int(s.get("total_expectations", 0)), int(s.get("successful", 0)),
                int(s.get("failed", 0)), float(s.get("success_percent", 0.0)),
            ),
        )
        return cur.fetchone()[0]


def insert_section(conn, run_id: int, section: str, block: dict, row_count: Optional[int]) -> int:
    st = block.get("statistics", {})
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_section
                (run_id, section, suite_name, success, evaluated, successful,
                 unsuccessful, success_percent, row_count)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING section_id
            """,
            (
                run_id, section, block.get("suite"),
                bool(block.get("success", False)),
                int(st.get("evaluated_expectations", 0)),
                int(st.get("successful_expectations", 0)),
                int(st.get("unsuccessful_expectations", 0)),
                float(st.get("success_percent", 0.0)),
                row_count,
            ),
        )
        return cur.fetchone()[0]


def insert_expectation(conn, section_id: int, fields: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_expectation
                (section_id, expectation_type, category, column_name, success,
                 expected_text, found_examples, affected_lines, unexpected_count, kwargs, result)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                section_id,
                fields["expectation_type"], fields["category"], fields["column_name"],
                fields["success"], fields["expected_text"], fields["found_examples"],
                fields["affected_lines"], fields["unexpected_count"],
                json.dumps(fields["kwargs"], ensure_ascii=False),
                json.dumps(fields["result"], ensure_ascii=False),
            ),
        )
