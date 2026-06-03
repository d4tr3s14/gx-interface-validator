"""
Tests del ETL de persistencia en PostgreSQL.

Se omiten automáticamente si psycopg no está instalado o si no hay una base de
datos disponible (p. ej. en CI sin Postgres). Para correrlos localmente:
    docker compose up -d db
    pip install -e ".[db]"
"""
import pytest

from interface_validator.config import DATA_DIR
from interface_validator.service import parse_and_validate

pytest.importorskip("psycopg")


def _db_available() -> bool:
    try:
        from interface_validator.db.connection import get_connection

        conn = get_connection()
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL no disponible")


def test_load_document_persists_run():
    from interface_validator.db import load_document

    _, document = parse_and_validate(DATA_DIR / "SAMPLE01_F20250404.FC", "sample01")
    run_id = load_document(document, project="DEMO", user="dleiva")
    assert isinstance(run_id, int) and run_id > 0


def test_unknown_project_raises_catalog_error():
    from interface_validator.db import CatalogError, load_document

    _, document = parse_and_validate(DATA_DIR / "SAMPLE01_F20250404.FC", "sample01")
    with pytest.raises(CatalogError):
        load_document(document, project="NO_EXISTE", user="dleiva")


def test_unknown_user_raises_catalog_error():
    from interface_validator.db import CatalogError, load_document

    _, document = parse_and_validate(DATA_DIR / "SAMPLE01_F20250404.FC", "sample01")
    with pytest.raises(CatalogError):
        load_document(document, project="DEMO", user="usuario_inexistente")


def test_load_comparison_persists_run():
    from interface_validator.comparison import compare_interfaces
    from interface_validator.db import load_comparison

    document = compare_interfaces(
        DATA_DIR / "SAMPLE01_F20250404.FC",
        DATA_DIR / "SAMPLE01_F20250402.FC",
        "sample01",
        mode="by_id",
    )
    comparison_run_id = load_comparison(document, project="DEMO", user="dleiva")
    assert isinstance(comparison_run_id, int) and comparison_run_id > 0
