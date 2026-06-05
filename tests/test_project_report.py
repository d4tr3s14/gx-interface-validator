"""Tests del informe consolidado por proyecto (se omiten sin PostgreSQL)."""
import pytest

pytest.importorskip("psycopg")


def _db_available() -> bool:
    try:
        from interface_validator.db.connection import get_connection

        get_connection().close()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL no disponible")


def test_generate_project_report(tmp_path):
    from interface_validator.db.connection import get_connection
    from interface_validator.reporting.project_report import generate_project_report

    conn = get_connection()
    try:
        outputs = generate_project_report(conn, "DEMO", tmp_path, fmt="html", embed=True)
    finally:
        conn.close()

    assert outputs["html"].exists()
    model = outputs["model"]
    assert "kpis" in model
    assert model["project"]["project_key"] == "DEMO"
    # El informe ejecutivo por interfaz (drill-down) también se generó
    assert any(p.name.startswith("Informe_") and p.suffix == ".html" for p in tmp_path.iterdir())
    # Veredicto de certificación presente y coherente
    cert = model["certification"]
    assert cert["verdict"] in ("APTO PARA CERTIFICAR", "NO APTO PARA CERTIFICAR")
    assert cert["apto"] == all(c["passed"] for c in cert["criteria"])


def test_unknown_project_raises():
    from interface_validator.db.connection import get_connection
    from interface_validator.reporting.project_report import generate_project_report

    conn = get_connection()
    try:
        with pytest.raises(ValueError):
            generate_project_report(conn, "NO_EXISTE_XYZ", "/tmp", fmt="html")
    finally:
        conn.close()
