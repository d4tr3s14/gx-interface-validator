"""
Runner de validación por sección sobre el motor de Great Expectations 1.x.

Dada una sección (header/body/footer) como DataFrame y su suite de expectativas,
ejecuta:
  1. Expectations nativas de GE        (built-in)
  2. Reglas semánticas traducidas a GE (translators.py)
  3. Expectations personalizadas        (custom_rules.py)

y devuelve un único diccionario normalizado por sección.
"""
from __future__ import annotations

import great_expectations as gx
import pandas as pd
from great_expectations.data_context.types.base import ProgressBarsConfig

from . import custom_rules, translators


def _camel(expectation_type: str) -> str:
    """expect_column_values_to_not_be_null -> ExpectColumnValuesToNotBeNull."""
    return "".join(part.capitalize() for part in expectation_type.split("_"))


def _ge_class(expectation_type: str):
    """Devuelve la clase de expectation de GE o None si no existe."""
    return getattr(gx.expectations, _camel(expectation_type), None)


def _empty_stats() -> dict:
    return {
        "evaluated_expectations": 0,
        "successful_expectations": 0,
        "unsuccessful_expectations": 0,
        "success_percent": 100.0,
    }


def _compute_stats(results: list[dict]) -> dict:
    total = len(results)
    ok = sum(1 for r in results if r["success"])
    return {
        "evaluated_expectations": total,
        "successful_expectations": ok,
        "unsuccessful_expectations": total - ok,
        "success_percent": round(ok / total * 100, 2) if total else 100.0,
    }


class GeSectionRunner:
    """Ejecuta una suite de expectativas sobre una sección usando GE 1.x."""

    def __init__(self):
        # Contexto efímero: no escribe nada en disco, ideal para CI.
        self.context = gx.get_context(mode="ephemeral")
        # Silencia las barras de progreso de GE ("Calculating Metrics...").
        self.context.variables.progress_bars = ProgressBarsConfig(
            globally=False, metric_calculations=False
        )

    def _make_batch(self, df: pd.DataFrame, section: str):
        data_source = self.context.data_sources.add_pandas(name=f"iv_src_{section}")
        asset = data_source.add_dataframe_asset(name=f"iv_asset_{section}")
        batch_def = asset.add_batch_definition_whole_dataframe(f"iv_bd_{section}")
        return batch_def.get_batch(batch_parameters={"dataframe": df})

    def _run_ge_expectation(self, batch, ge_type: str, ge_kwargs: dict) -> dict:
        exp_class = _ge_class(ge_type)
        if exp_class is None:
            return {"success": False, "result": {"error": f"GE no conoce '{ge_type}'"}}

        # Se pide COMPLETE para capturar los valores inesperados en el reporte.
        kwargs_with_format = {**ge_kwargs, "result_format": "COMPLETE"}
        try:
            expectation = exp_class(**kwargs_with_format)
        except TypeError:
            expectation = exp_class(**ge_kwargs)

        validation = batch.validate(expectation)
        as_dict = validation.to_json_dict()
        return {
            "success": bool(as_dict.get("success", False)),
            "result": as_dict.get("result", {}),
        }

    def run(self, df: pd.DataFrame, suite_entries: list[dict], section: str, suite_name: str) -> dict:
        results: list[dict] = []
        batch = None

        for entry in suite_entries:
            etype = entry["expectation_type"]
            kwargs = entry.get("kwargs", {})

            # 1) Expectations personalizadas (no van por GE)
            if custom_rules.is_custom(etype):
                results.append(custom_rules.run_custom(etype, df, kwargs))
                continue

            # 2) Reglas semánticas -> se traducen a GE; 3) built-in de GE
            if translators.is_semantic(etype):
                ge_type, ge_kwargs = translators.translate(etype, kwargs)
                label = etype  # se reporta con el nombre semántico original
            else:
                ge_type, ge_kwargs, label = etype, kwargs, etype

            if batch is None:
                batch = self._make_batch(df, section)

            outcome = self._run_ge_expectation(batch, ge_type, ge_kwargs)
            results.append(
                {
                    "expectation_type": label,
                    "kwargs": kwargs,
                    "success": outcome["success"],
                    "result": outcome["result"],
                }
            )

        stats = _compute_stats(results) if results else _empty_stats()
        return {
            "section": section,
            "suite": suite_name,
            "success": all(r["success"] for r in results) if results else True,
            "statistics": stats,
            "results": results,
        }


def run_section(df: pd.DataFrame, suite_entries: list[dict], section: str, suite_name: str) -> dict:
    """Atajo funcional para validar una sección."""
    return GeSectionRunner().run(df, suite_entries, section, suite_name)
