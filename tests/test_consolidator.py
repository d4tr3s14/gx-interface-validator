"""Tests del consolidador y del orquestador de alto nivel."""
from interface_validator.config import DATA_DIR
from interface_validator.service import validate_interface


def test_single_document_has_all_sections():
    doc = validate_interface(DATA_DIR / "SAMPLE01_F20250404.FC", write=False)
    assert set(doc["sections"]) == {"header", "body", "footer", "cross_section"}


def test_valid_interface_passes():
    doc = validate_interface(DATA_DIR / "SAMPLE01_F20250404.FC", write=False)
    assert doc["summary"]["success"] is True
    assert doc["summary"]["failed"] == 0


def test_broken_interface_fails_with_expected_sections():
    doc = validate_interface(DATA_DIR / "SAMPLE01_F20250402.FC", write=False)
    assert doc["summary"]["success"] is False
    assert doc["sections"]["header"]["success"] is False
    assert doc["sections"]["body"]["success"] is False
    assert doc["sections"]["cross_section"]["success"] is False
    # El footer del ejemplo roto está bien formado en sí mismo
    assert doc["sections"]["footer"]["success"] is True


def test_aggregate_statistics_are_consistent():
    doc = validate_interface(DATA_DIR / "SAMPLE01_F20250404.FC", write=False)
    summary = doc["summary"]
    total = sum(b["statistics"]["evaluated_expectations"] for b in doc["sections"].values())
    assert summary["total_expectations"] == total


def test_metadata_present():
    doc = validate_interface(DATA_DIR / "SAMPLE01_F20250404.FC", write=False)
    assert doc["interface"] == "SAMPLE01"
    assert doc["interface_date"] == "20250404"
    assert "executed_at" in doc
