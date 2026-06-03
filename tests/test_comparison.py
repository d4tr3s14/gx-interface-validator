"""Tests del motor de comparación de interfaces (by_line / by_id)."""
from interface_validator.comparison import compare_interfaces
from interface_validator.config import DATA_DIR

A = DATA_DIR / "SAMPLE01_F20250404.FC"
B = DATA_DIR / "SAMPLE01_F20250402.FC"  # versión con diferencias


def test_by_line_identical_is_100_percent():
    doc = compare_interfaces(A, A, "sample01", mode="by_line")
    assert doc["mode"] == "by_line"
    assert doc["summary"]["match_percent"] == 100.0
    assert doc["summary"]["differing"] == 0
    assert set(doc["sections"]) == {"whole_file"}


def test_by_line_detects_differences():
    doc = compare_interfaces(A, B, "sample01", mode="by_line")
    s = doc["summary"]
    assert s["differing"] > 0 or s["only_in_a"] > 0 or s["only_in_b"] > 0
    assert s["match_percent"] < 100.0


def test_by_id_uses_layout_key_and_detects_diffs():
    doc = compare_interfaces(A, B, "sample01", mode="by_id")
    assert doc["key_columns"] == ["ENTRY_ID"]
    assert "body" in doc["sections"]
    # A tiene 8 ENTRY_ID; B tiene menos -> hay registros solo en A
    assert doc["sections"]["body"]["only_in_a"] >= 1


def test_by_id_key_override():
    doc = compare_interfaces(A, B, "sample01", mode="by_id", key_columns=["ENTRY_ID"])
    assert doc["key_columns"] == ["ENTRY_ID"]
