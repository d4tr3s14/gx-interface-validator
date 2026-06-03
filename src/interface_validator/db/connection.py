"""Conexión a PostgreSQL (configurable por entorno)."""
from __future__ import annotations

import os


def database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://gx:gx@localhost:5432/gx")


def get_connection():
    """Abre una conexión psycopg. Lanza ImportError si psycopg no está instalado."""
    import psycopg  # import perezoso (dependencia opcional del extra [db])

    return psycopg.connect(database_url())
