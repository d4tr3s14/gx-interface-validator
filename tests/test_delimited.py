"""Tests del soporte de interfaces delimitadas (CSV / ; / | / tab)."""
from interface_validator.config import DATA_DIR
from interface_validator.parser import DelimitedParser, load_layout, make_parser
from interface_validator.service import parse_and_validate


def test_make_parser_selects_delimited_for_csv_layout():
    layout = load_layout("sample04")
    assert isinstance(make_parser(layout), DelimitedParser)


def test_delimited_parsing_splits_sections_and_columns():
    layout = load_layout("sample04")
    parsed = make_parser(layout).parse_file(DATA_DIR / "SAMPLE04_F20250404.FC")
    assert len(parsed["header"]) == 1
    assert len(parsed["footer"]) == 1
    assert len(parsed["body"]) == 12
    assert list(parsed["body"].columns) == ["TXN_ID", "ACCOUNT", "CURRENCY", "AMOUNT", "STATUS"]
    assert parsed["header"]["REC_TYPE"].iloc[0] == "HDR"
    assert parsed["footer"]["REC_TYPE"].iloc[0] == "EOF"


def test_delimited_interface_validates_ok():
    _, document = parse_and_validate(DATA_DIR / "SAMPLE04_F20250404.FC", "sample04")
    assert document["summary"]["success"] is True
    assert set(document["sections"]) == {"header", "body", "footer", "cross_section"}
