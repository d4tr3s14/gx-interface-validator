"""Tests del motor: traductores semánticos y expectations personalizadas."""
import pandas as pd

from interface_validator.engine import custom_rules, translators


def test_numeric_translator_integer():
    ge_type, kwargs = translators.translate(
        "expect_column_values_to_be_numeric",
        {"column": "X", "permitir_negativos": False, "permitir_decimales": False},
    )
    assert ge_type == "expect_column_values_to_match_regex"
    assert kwargs["regex"] == r"^\d+$"


def test_numeric_translator_decimals_and_sign():
    _, kwargs = translators.translate(
        "expect_column_values_to_be_numeric",
        {"column": "X", "permitir_negativos": True, "permitir_decimales": True},
    )
    assert kwargs["regex"] == r"^-?\d+(\.\d+)?$"


def test_no_duplicate_rows_detects_duplicates():
    df = pd.DataFrame({"A": ["1", "1"], "B": ["x", "x"]}, dtype="string")
    result = custom_rules.run_custom("expect_table_to_have_no_duplicate_rows", df, {})
    assert result["success"] is False
    assert result["result"]["unexpected_count"] == 2


def test_no_duplicate_rows_passes_when_unique():
    df = pd.DataFrame({"A": ["1", "2"]}, dtype="string")
    result = custom_rules.run_custom("expect_table_to_have_no_duplicate_rows", df, {})
    assert result["success"] is True
