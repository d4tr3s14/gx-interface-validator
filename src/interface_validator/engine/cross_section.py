"""
Reglas de negocio que cruzan varias secciones de la interfaz.

Estas validaciones comparan el footer (totales declarados) contra el body
(detalle real). Se definen de forma **declarativa** en el layout YAML
(`business_rules`), de modo que cada interfaz aporte las suyas sin tocar código.

Tipos de regla soportados:
  * footer_count_matches_body : un campo del footer == nº de filas del body
  * footer_sum_matches_body   : un campo del footer == suma de un campo del body
                                (con filtro opcional `where`)
"""
from __future__ import annotations

import pandas as pd


def _to_int(value: str) -> int:
    value = (value or "").strip()
    return int(value) if value.lstrip("-").isdigit() else 0


def _result(name: str, success: bool, expected, observed) -> dict:
    return {
        "expectation_type": name,
        "kwargs": {},
        "success": success,
        "result": {"expected_value": expected, "observed_value": observed},
    }


def _footer_count_matches_body(rule: dict, body: pd.DataFrame, footer: pd.DataFrame) -> dict:
    col = rule["footer_column"]
    declared = _to_int(footer.iloc[0][col]) if len(footer) else 0
    actual = int(len(body))
    return _result(rule.get("name", "footer_count_matches_body"), declared == actual, declared, actual)


def _footer_sum_matches_body(rule: dict, body: pd.DataFrame, footer: pd.DataFrame) -> dict:
    footer_col = rule["footer_column"]
    body_col = rule["body_column"]
    declared = _to_int(footer.iloc[0][footer_col]) if len(footer) else 0

    df = body
    where = rule.get("where")
    if where and where["column"] in body:
        mask = body[where["column"]].astype("string").str.strip() == where["equals"]
        df = body.loc[mask]

    actual = int(sum(_to_int(v) for v in df.get(body_col, []))) if body_col in body else 0
    return _result(rule.get("name", "footer_sum_matches_body"), declared == actual, declared, actual)


_RULE_TYPES = {
    "footer_count_matches_body": _footer_count_matches_body,
    "footer_sum_matches_body": _footer_sum_matches_body,
}


def run_cross_section(sections: dict[str, pd.DataFrame], business_rules: list[dict] | None = None) -> dict:
    """Ejecuta las reglas de negocio declaradas en el layout."""
    body = sections.get("body", pd.DataFrame())
    footer = sections.get("footer", pd.DataFrame())

    results: list[dict] = []
    for rule in business_rules or []:
        handler = _RULE_TYPES.get(rule.get("type"))
        if handler is None:
            continue
        results.append(handler(rule, body, footer))

    total = len(results)
    ok = sum(1 for r in results if r["success"])
    return {
        "section": "cross_section",
        "suite": "business_rules",
        "success": ok == total,
        "statistics": {
            "evaluated_expectations": total,
            "successful_expectations": ok,
            "unsuccessful_expectations": total - ok,
            "success_percent": round(ok / total * 100, 2) if total else 100.0,
        },
        "results": results,
    }
