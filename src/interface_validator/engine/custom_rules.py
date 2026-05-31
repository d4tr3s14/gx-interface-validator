"""
Expectations personalizadas que no existen como built-in de Great Expectations.

Se implementan como validadores sobre el DataFrame y devuelven un resultado en
el MISMO formato normalizado que usa el resto del motor, de modo que el
consolidador y el reporte Allure los traten igual que a las expectations de GE.

Es el punto de extensión natural para que un QA automatizador agregue reglas
propias: basta registrar una función en ``CUSTOM_EXPECTATIONS``.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd


def expect_table_to_have_no_duplicate_rows(df: pd.DataFrame, kwargs: dict) -> dict:
    """Verifica que la tabla no tenga filas completamente duplicadas."""
    max_details = int(kwargs.get("max_error_details", 20))
    duplicated_mask = df.duplicated(keep=False)
    dup_count = int(duplicated_mask.sum())

    sample = (
        df[duplicated_mask]
        .head(max_details)
        .to_dict(orient="records")
    )

    return {
        "success": dup_count == 0,
        "result": {
            "element_count": int(len(df)),
            "unexpected_count": dup_count,
            "unexpected_percent": round(dup_count / len(df) * 100, 4) if len(df) else 0.0,
            "partial_unexpected_list": sample,
        },
    }


# Registro de expectations personalizadas
CUSTOM_EXPECTATIONS: dict[str, Callable[[pd.DataFrame, dict], dict]] = {
    "expect_table_to_have_no_duplicate_rows": expect_table_to_have_no_duplicate_rows,
}


def is_custom(expectation_type: str) -> bool:
    return expectation_type in CUSTOM_EXPECTATIONS


def run_custom(expectation_type: str, df: pd.DataFrame, kwargs: dict) -> dict:
    outcome = CUSTOM_EXPECTATIONS[expectation_type](df, kwargs)
    return {
        "expectation_type": expectation_type,
        "kwargs": {k: v for k, v in kwargs.items()},
        "success": outcome["success"],
        "result": outcome.get("result", {}),
    }
