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

CARDS = [
    {
        "name": "Validaciones y comparaciones por proyecto",
        "sql": "SELECT project_key, validaciones, comparaciones FROM vw_project_dashboard ORDER BY validaciones DESC",
        "display": "bar",
    },
    {
        "name": "% de éxito promedio por proyecto",
        "sql": "SELECT project_key, pct_exito_promedio FROM vw_project_dashboard WHERE pct_exito_promedio IS NOT NULL ORDER BY pct_exito_promedio DESC",
        "display": "bar",
    },
    {
        "name": "Errores más comunes",
        "sql": "SELECT category, column_name, ocurrencias, datos_afectados FROM vw_top_errors LIMIT 10",
        "display": "table",
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
        r.raise_for_status()
        return r.json()["id"]

    print("Metabase ya configurado; iniciando sesión...")
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


def create_dashboard(headers: dict, card_ids: list[int]) -> int:
    r = requests.post(f"{MB}/api/dashboard", headers=headers, timeout=30,
                      json={"name": "GX — Reportería de validaciones"})
    r.raise_for_status()
    dash_id = r.json()["id"]

    # Distribución 2x2 (grilla de 18 columnas de Metabase).
    layout = [(0, 0), (9, 0), (0, 7), (9, 7)]
    dashcards = []
    for (col, row), card_id in zip(layout, card_ids):
        dashcards.append({
            "id": -(card_id), "card_id": card_id,
            "row": row, "col": col, "size_x": 9, "size_y": 7,
            "parameter_mappings": [], "visualization_settings": {},
        })
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
