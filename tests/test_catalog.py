"""Tests del comando de catálogo (se omiten si no hay PostgreSQL)."""
import pytest

from interface_validator.config import DATA_DIR
from interface_validator.service import parse_and_validate

pytest.importorskip("psycopg")


def _db_available() -> bool:
    try:
        from interface_validator.db.connection import get_connection

        get_connection().close()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL no disponible")


def test_add_catalog_then_persist():
    """Tras dar de alta proyecto y usuario, una validación bajo ellos se persiste."""
    from interface_validator.db import load_document
    from interface_validator.db import repository as repo
    from interface_validator.db.connection import get_connection

    conn = get_connection()
    repo.add_project(conn, "QA_TEST", "Proyecto de prueba", "QA")
    repo.add_user(conn, "qa_tester", "QA Tester")
    conn.commit()
    conn.close()

    _, document = parse_and_validate(DATA_DIR / "SAMPLE01_F20250404.FC", "sample01")
    run_id = load_document(document, project="QA_TEST", user="qa_tester")
    assert isinstance(run_id, int) and run_id > 0


def test_add_project_is_idempotent():
    from interface_validator.db import repository as repo
    from interface_validator.db.connection import get_connection

    conn = get_connection()
    id1 = repo.add_project(conn, "QA_TEST2", "Prueba 2")
    id2 = repo.add_project(conn, "QA_TEST2", "Prueba 2 (actualizada)")
    conn.commit()
    conn.close()
    assert id1 == id2
