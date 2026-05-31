"""Tests del parser de ancho fijo."""
from interface_validator.config import DATA_DIR
from interface_validator.parser import FixedWidthParser, load_layout


def _parsed():
    layout = load_layout("sample01")
    return FixedWidthParser(layout).parse_file(DATA_DIR / "SAMPLE01_F20250404.FC")


def test_classifies_three_sections():
    parsed = _parsed()
    assert set(parsed.sections) == {"header", "body", "footer"}


def test_header_and_footer_are_single_row():
    parsed = _parsed()
    assert len(parsed["header"]) == 1
    assert len(parsed["footer"]) == 1
    assert len(parsed["body"]) == 8


def test_columns_match_layout():
    parsed = _parsed()
    assert list(parsed["header"].columns) == [
        "REC_TYPE", "SYSTEM_CODE", "FILE_CODE", "PROCESS_DATE", "PROCESS_TYPE", "FILLER_H"
    ]


def test_preserves_leading_zeros_and_spaces():
    parsed = _parsed()
    # FISCAL_PERIOD conserva los espacios finales: "FY2025   "
    assert parsed["body"]["FISCAL_PERIOD"].iloc[0] == "FY2025   "
    # AMOUNT_LOCAL conserva ceros a la izquierda (longitud fija 19)
    assert len(parsed["body"]["AMOUNT_LOCAL"].iloc[0]) == 19


def test_markers_route_correctly():
    parsed = _parsed()
    assert parsed["header"]["REC_TYPE"].iloc[0] == "HDR"
    assert parsed["footer"]["REC_TYPE"].iloc[0] == "TLR"
