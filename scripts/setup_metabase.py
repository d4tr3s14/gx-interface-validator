"""
Autoconfiguración de Metabase para la reportería de validaciones.

Hace, de forma idempotente y vía la API de Metabase:
  1. Setup inicial (usuario admin) — o login si ya está configurado.
  2. Conexión a la base de datos PostgreSQL `gx`.
  3. Preguntas (cards) en SQL sobre las vistas vw_* y un dashboard que las agrupa.

Requisitos:
    docker compose up -d            # db + metabase
    python scripts/setup_metabase.py

Variables de entorno (con valores por defecto para el demo):
    MB_URL=http://localhost:3000
    MB_ADMIN_EMAIL=admin@gx.local   MB_ADMIN_PASSWORD=gxgxgxgx1
"""
from __future__ import annotations

import os
import sys
import time

import requests

MB = os.getenv("MB_URL", "http://localhost:3000").rstrip("/")
EMAIL = os.getenv("MB_ADMIN_EMAIL", "admin@gx.local")
PASSWORD = os.getenv("MB_ADMIN_PASSWORD", "gxgxgxgx1")

# Conexión a la BD de resultados (Metabase corre en la red de compose -> host "db").
PG = {
    "host": os.getenv("MB_PG_HOST", "db"),
    "port": int(os.getenv("MB_PG_PORT", "5432")),
    "dbname": os.getenv("MB_PG_DB", "gx"),
    "user": os.getenv("MB_PG_USER", "gx"),
    "password": os.getenv("MB_PG_PASSWORD", "gx"),
}

# URL del servidor de informes (servicio nginx 'reports') para el panel de enlace.
REPORTS_URL = os.getenv("REPORTS_URL", "http://localhost:8080")

CARDS = [
    {  # KPI grande
        "name": "Interfaces validadas (total)",
        "sql": "SELECT COUNT(DISTINCT interface_id) AS interfaces FROM fact_run",
        "display": "scalar",
    },
    {  # KPI grande
        "name": "% de éxito promedio",
        "sql": "SELECT ROUND(AVG(success_percent)::numeric, 1) AS pct FROM fact_run",
        "display": "scalar",
    },
    {  # KPI grande
        "name": "Comparaciones (total)",
        "sql": "SELECT COUNT(*) AS comparaciones FROM fact_comparison_run",
        "display": "scalar",
    },
    {
        "name": "Validaciones y comparaciones por proyecto",
        "sql": "SELECT project_key, validaciones, comparaciones FROM vw_project_dashboard ORDER BY validaciones DESC",
        "display": "bar",
    },
    {
        "name": "Errores más comunes",
        "sql": "SELECT category || ' · ' || COALESCE(column_name, '—') AS error, ocurrencias "
               "FROM vw_top_errors LIMIT 8",
        "display": "row",
    },
    {
        "name": "Actividad por interfaz",
        "sql": "SELECT project_key, interface, validada, comparada FROM vw_interface_activity ORDER BY project_key, interface",
        "display": "table",
    },
]


def wait_healthy(timeout: int = 180) -> None:
    print(f"Esperando a Metabase en {MB} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{MB}/api/health", timeout=5)
            if r.ok and r.json().get("status") == "ok":
                print("Metabase listo.")
                return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(5)
    raise SystemExit("Metabase no respondió a tiempo.")


def get_session() -> str:
    """Hace el setup inicial (si procede) o inicia sesión. Devuelve el session id."""
    props = requests.get(f"{MB}/api/session/properties", timeout=10).json()
    token = props.get("setup-token")

    if token:
        print("Ejecutando setup inicial (admin + base de datos)...")
        payload = {
            "token": token,
            "user": {
                "first_name": "Admin", "last_name": "GX",
                "email": EMAIL, "password": PASSWORD,
                "site_name": "GX Interface Validator",
            },
            "prefs": {"site_name": "GX Interface Validator", "allow_tracking": False},
            "database": {
                "engine": "postgres",
                "name": "GX Resultados",
                "details": {**PG, "ssl": False},
            },
        }
        r = requests.post(f"{MB}/api/setup", json=payload, timeout=60)
        if r.ok:
            return r.json()["id"]
        # Token obsoleto / ya configurado -> caer a login.
        print("Setup no aplicable (ya configurado); iniciando sesión...")

    print("Iniciando sesión en Metabase...")
    r = requests.post(f"{MB}/api/session", json={"username": EMAIL, "password": PASSWORD}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def get_database_id(headers: dict) -> int:
    dbs = requests.get(f"{MB}/api/database", headers=headers, timeout=30).json()
    data = dbs.get("data", dbs) if isinstance(dbs, dict) else dbs
    for db in data:
        details = db.get("details", {}) or {}
        if db.get("engine") == "postgres" and details.get("dbname") == PG["dbname"]:
            return db["id"]
    # Si no existe (login sin setup), crearla.
    r = requests.post(f"{MB}/api/database", headers=headers, timeout=60, json={
        "engine": "postgres", "name": "GX Resultados", "details": {**PG, "ssl": False},
    })
    r.raise_for_status()
    return r.json()["id"]


def create_card(headers: dict, db_id: int, card: dict) -> int:
    body = {
        "name": card["name"],
        "display": card["display"],
        "dataset_query": {
            "type": "native",
            "native": {"query": card["sql"]},
            "database": db_id,
        },
        "visualization_settings": {},
    }
    r = requests.post(f"{MB}/api/card", headers=headers, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def _text_card(neg_id: int, text: str, row: int, col: int, w: int, h: int) -> dict:
    """Tarjeta de texto (markdown) virtual para el dashboard."""
    return {
        "id": neg_id, "card_id": None, "row": row, "col": col, "size_x": w, "size_y": h,
        "parameter_mappings": [],
        "visualization_settings": {
            "virtual_card": {"name": None, "display": "text",
                             "visualization_settings": {}, "dataset_query": {}, "archived": False},
            "text": text, "text.align_vertical": "middle",
        },
    }


def create_dashboard(headers: dict, card_ids: list[int]) -> int:
    r = requests.post(f"{MB}/api/dashboard", headers=headers, timeout=30,
                      json={"name": "GX — Reportería de validaciones"})
    r.raise_for_status()
    dash_id = r.json()["id"]

    # card_ids en orden de CARDS:
    #   0,1,2 = scalars · 3 = barras por proyecto · 4 = errores (row) · 5 = actividad (tabla)
    grid = [
        (card_ids[0], 3, 0, 6, 3),    # scalar interfaces validadas
        (card_ids[1], 3, 6, 6, 3),    # scalar % éxito
        (card_ids[2], 3, 12, 6, 3),   # scalar comparaciones
        (card_ids[3], 6, 0, 9, 7),    # barras por proyecto
        (card_ids[4], 6, 9, 9, 7),    # errores más comunes (row)
        (card_ids[5], 13, 0, 18, 7),  # actividad por interfaz (tabla)
    ]
    dashcards = [
        {"id": -(cid), "card_id": cid, "row": r0, "col": c0, "size_x": w, "size_y": h,
         "parameter_mappings": [], "visualization_settings": {}}
        for (cid, r0, c0, w, h) in grid
    ]
    # Panel de texto superior con el enlace de descarga del informe consolidado.
    dashcards.append(_text_card(
        -9001,
        "### 📄 Informe consolidado por proyecto\n"
        "Genera el informe formal (HTML/PDF) con `project-report --project <KEY>` y "
        f"descárgalo desde el **[servidor de informes]({REPORTS_URL}/)** "
        f"(ej.: [Informe_Proyecto_RIESGO]({REPORTS_URL}/Informe_Proyecto_RIESGO.html)).",
        row=0, col=0, w=18, h=3,
    ))

    r = requests.put(f"{MB}/api/dashboard/{dash_id}", headers=headers, timeout=60,
                     json={"dashcards": dashcards})
    r.raise_for_status()
    return dash_id


def main() -> int:
    wait_healthy()
    session = get_session()
    headers = {"X-Metabase-Session": session}

    db_id = get_database_id(headers)
    print(f"Base de datos en Metabase: id={db_id}")

    card_ids = [create_card(headers, db_id, c) for c in CARDS]
    print(f"Preguntas creadas: {card_ids}")

    dash_id = create_dashboard(headers, card_ids)
    print("\nListo. Dashboard disponible en:")
    print(f"  {MB}/dashboard/{dash_id}")
    print(f"  (login: {EMAIL} / {PASSWORD})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
