"""
Traductores de reglas "semánticas" a expectations nativas de Great Expectations.

Un QA automatizador puede escribir reglas de alto nivel y legibles para el
negocio (p. ej. "esta columna debe contener solo números") y este módulo las
convierte a una expectation nativa de GE (normalmente basada en regex).

Así se obtiene lo mejor de ambos mundos:
  * vocabulario de negocio en las suites,
  * ejecución real sobre el motor de Great Expectations.

Cada traductor recibe los kwargs de la regla semántica y devuelve una tupla:
    (ge_expectation_type, ge_kwargs)
"""
from __future__ import annotations

from typing import Callable


def _numeric_regex(permitir_negativos: bool, permitir_decimales: bool) -> str:
    sign = "-?" if permitir_negativos else ""
    if permitir_decimales:
        return rf"^{sign}\d+(\.\d+)?$"
    return rf"^{sign}\d+$"


def translate_numeric(kwargs: dict) -> tuple[str, dict]:
    """`expect_column_values_to_be_numeric` -> regex sobre la columna."""
    regex = _numeric_regex(
        permitir_negativos=kwargs.get("permitir_negativos", False),
        permitir_decimales=kwargs.get("permitir_decimales", False),
    )
    return "expect_column_values_to_match_regex", {
        "column": kwargs["column"],
        "regex": regex,
    }


def translate_balance_format(kwargs: dict) -> tuple[str, dict]:
    """
    `expect_column_values_to_match_balance_format` -> regex sobre la columna.

    Un "saldo" es un importe entero (relleno con ceros a la izquierda) con un
    número fijo de decimales implícitos y, opcionalmente, un signo.
    """
    decimales = int(kwargs.get("decimales", 0))
    signo = "[+-]?" if kwargs.get("signo_obligatorio", False) else "[+-]?"
    if decimales > 0:
        regex = rf"^{signo}\d+\.\d{{{decimales}}}$"
    else:
        regex = rf"^{signo}\d+$"
    return "expect_column_values_to_match_regex", {
        "column": kwargs["column"],
        "regex": regex,
    }


# Registro de reglas semánticas -> traductor
SEMANTIC_TRANSLATORS: dict[str, Callable[[dict], tuple[str, dict]]] = {
    "expect_column_values_to_be_numeric": translate_numeric,
    "expect_column_values_to_match_balance_format": translate_balance_format,
}


def is_semantic(expectation_type: str) -> bool:
    return expectation_type in SEMANTIC_TRANSLATORS


def translate(expectation_type: str, kwargs: dict) -> tuple[str, dict]:
    return SEMANTIC_TRANSLATORS[expectation_type](kwargs)
