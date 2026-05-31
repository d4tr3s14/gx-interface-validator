"""
Taxonomía de expectativas para el informe de cara al usuario.

Traduce los nombres técnicos de las expectativas a categorías y descripciones
legibles por un Product Owner o el responsable de la interfaz.
"""
from __future__ import annotations

# expectation_type -> (categoría, subtipo legible)
TAXONOMY: dict[str, tuple[str, str]] = {
    "expect_table_columns_to_match_set": ("Completitud", "Columnas con nombre correcto"),
    "expect_column_to_exist": ("Completitud", "Columna presente"),
    "expect_column_values_to_not_be_null": ("Completitud", "Sin valores nulos"),
    "expect_column_value_lengths_to_equal": ("Formato", "Largo de campo correcto"),
    "expect_column_values_to_be_in_set": ("Dominio", "Valores dentro del conjunto permitido"),
    "expect_column_values_to_be_unique": ("Unicidad", "Valores únicos (sin duplicados)"),
    "expect_table_to_have_no_duplicate_rows": ("Unicidad", "Sin registros duplicados"),
    "expect_column_values_to_be_numeric": ("Formato", "Solo caracteres numéricos"),
    "expect_column_values_to_match_balance_format": ("Formato", "Formato de saldo correcto"),
    "expect_column_values_to_match_regex": ("Formato", "Cumple el patrón requerido"),
}

CATEGORY_ORDER = ["Completitud", "Dominio", "Formato", "Unicidad", "Negocio"]


def categorize(expectation_type: str, section: str) -> tuple[str, str]:
    """Devuelve (categoría, subtipo) legible para una expectativa."""
    if section == "cross_section":
        return "Negocio", expectation_type
    return TAXONOMY.get(expectation_type, ("Otros", expectation_type))


def expected_text(result: dict) -> str:
    """Construye una descripción legible del valor esperado por la expectativa."""
    etype = result.get("expectation_type", "")
    kwargs = result.get("kwargs", {})
    res = result.get("result", {})

    if etype == "expect_column_values_to_be_in_set":
        valores = ", ".join(str(v) for v in kwargs.get("value_set", []))
        return f"Valores permitidos: {valores}"
    if etype == "expect_table_columns_to_match_set":
        return f"Debe contener {len(kwargs.get('column_set', []))} columnas específicas"
    if etype == "expect_column_values_to_not_be_null":
        return "Sin valores nulos"
    if etype == "expect_column_values_to_be_unique":
        return "Valores únicos (sin duplicados)"
    if etype == "expect_column_value_lengths_to_equal":
        return f"Largo exacto: {kwargs.get('value')}"
    if etype == "expect_column_values_to_be_numeric":
        return "Solo caracteres numéricos"
    if etype == "expect_column_values_to_match_balance_format":
        return "Formato de saldo válido"
    if "expected_value" in res:
        return f"Valor esperado: {res.get('expected_value')}"
    return "Cumplir la regla definida"


def error_count(result: dict) -> int:
    """Número de datos afectados por una expectativa fallida."""
    res = result.get("result", {})
    if "unexpected_count" in res:
        return int(res.get("unexpected_count") or 0)
    # reglas cross-section: 1 desviación de total
    return 0 if result.get("success") else 1


def column_of(result: dict) -> str:
    return result.get("kwargs", {}).get("column", "Expectativa general")


def error_examples(result: dict) -> dict:
    """
    Describe DÓNDE está el error: valores encontrados y líneas afectadas.

    Returns:
        dict con 'found' (valores que fallaron) y 'lines' (números de línea).
    """
    etype = result.get("expectation_type", "")
    kwargs = result.get("kwargs", {})
    res = result.get("result", {})

    # Reglas de negocio (cross-section): declarado vs. calculado
    if "observed_value" in res and "expected_value" in res:
        return {
            "found": f"declarado: {res['expected_value']} · calculado: {res['observed_value']}",
            "lines": "footer",
        }

    # Estructura de columnas
    if etype == "expect_table_columns_to_match_set":
        expected = set(kwargs.get("column_set", []))
        observed = set(res.get("observed_value", []) or [])
        partes = []
        if expected - observed:
            partes.append("faltan: " + ", ".join(sorted(expected - observed)))
        if observed - expected:
            partes.append("sobran: " + ", ".join(sorted(observed - expected)))
        return {"found": "; ".join(partes) or "estructura de columnas distinta", "lines": ""}

    # Expectations por valor: muestra de valores inesperados (sin repetir)
    sample = res.get("partial_unexpected_list") or res.get("unexpected_list") or []
    seen: list = []
    for v in sample:
        if v not in seen:
            seen.append(v)
    found = ", ".join(f"'{v}'" for v in seen[:8])

    idx = res.get("partial_unexpected_index_list") or res.get("unexpected_index_list") or []
    # +1 porque la fila 0 del body es la línea 1 de datos
    lines = ", ".join(str(int(i) + 1) for i in idx[:8] if isinstance(i, int))

    return {"found": found, "lines": lines}
