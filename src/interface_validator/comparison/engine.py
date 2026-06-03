"""
Motor de comparación de interfaces (A vs B).

Dos modos:
  * by_line : compara el archivo completo línea a línea (posicional).
  * by_id   : parsea ambos archivos con el layout y compara registro a registro
              por columnas clave, **por sección** (header/body/footer).

Produce un documento consolidado de comparación (1 por comparación) con un
resumen global y el detalle por sección, listo para reportar o persistir.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..parser import load_layout, make_parser

MAX_DIFFS = 50  # tope de diferencias detalladas por sección (como el original)


def _read_lines(path: str | Path) -> list[str]:
    with open(path, "r", encoding="latin-1") as f:
        return [line.rstrip("\r\n") for line in f if line.strip() != ""]


def _empty_section() -> dict:
    return {
        "elements_a": 0, "elements_b": 0,
        "only_in_a": 0, "only_in_b": 0, "differing": 0,
        "match_percent": 100.0, "diffs": [],
    }


# --------------------------------------------------------------------------- #
# Modo por línea (posicional)
# --------------------------------------------------------------------------- #
def compare_by_line(file_a: str | Path, file_b: str | Path) -> dict:
    lines_a = _read_lines(file_a)
    lines_b = _read_lines(file_b)
    n = max(len(lines_a), len(lines_b))

    matched = only_a = only_b = differing = 0
    diffs: list[dict] = []

    for i in range(n):
        a = lines_a[i] if i < len(lines_a) else None
        b = lines_b[i] if i < len(lines_b) else None
        if a is not None and b is not None:
            if a == b:
                matched += 1
            else:
                differing += 1
                if len(diffs) < MAX_DIFFS:
                    diffs.append({
                        "row_id": f"line_{i + 1}", "discrepancy_type": "value_differs",
                        "column_name": None, "value_a": a[:500], "value_b": b[:500],
                        "line_a": i + 1, "line_b": i + 1,
                    })
        elif a is not None:
            only_a += 1
            if len(diffs) < MAX_DIFFS:
                diffs.append({"row_id": f"line_{i + 1}", "discrepancy_type": "only_in_a",
                              "column_name": None, "value_a": a[:500], "value_b": None,
                              "line_a": i + 1, "line_b": None})
        else:
            only_b += 1
            if len(diffs) < MAX_DIFFS:
                diffs.append({"row_id": f"line_{i + 1}", "discrepancy_type": "only_in_b",
                              "column_name": None, "value_a": None, "value_b": b[:500],
                              "line_a": None, "line_b": i + 1})

    return {
        "elements_a": len(lines_a), "elements_b": len(lines_b),
        "only_in_a": only_a, "only_in_b": only_b, "differing": differing,
        "match_percent": round(matched / n * 100, 2) if n else 100.0,
        "diffs": diffs,
    }


# --------------------------------------------------------------------------- #
# Modo por ID (por sección, usando columnas clave)
# --------------------------------------------------------------------------- #
def _effective_keys(df: pd.DataFrame, keys: list[str] | None) -> list[str] | None:
    if keys and all(k in df.columns for k in keys):
        return keys
    return None  # posicional (por índice de fila)


def _index_rows(df: pd.DataFrame, keys: list[str] | None) -> dict:
    index = {}
    for i, (_, row) in enumerate(df.iterrows()):
        key = tuple(str(row[k]) for k in keys) if keys else (i,)
        index[key] = (i, row)
    return index


def compare_section(df_a: pd.DataFrame, df_b: pd.DataFrame, keys: list[str] | None) -> dict:
    eff = _effective_keys(df_a, keys)
    index_a = _index_rows(df_a, eff)
    index_b = _index_rows(df_b, eff)

    keys_a, keys_b = set(index_a), set(index_b)
    only_a_keys = keys_a - keys_b
    only_b_keys = keys_b - keys_a
    common = keys_a & keys_b

    # Columnas a comparar (todas menos las clave)
    compare_cols = [c for c in df_a.columns if not (eff and c in eff)]

    diffs: list[dict] = []
    differing = 0

    def _row_id(key) -> str:
        return "|".join(str(x) for x in key)

    for key in only_a_keys:
        i, _ = index_a[key]
        if len(diffs) < MAX_DIFFS:
            diffs.append({"row_id": _row_id(key), "discrepancy_type": "only_in_a",
                          "column_name": None, "value_a": None, "value_b": None,
                          "line_a": i + 1, "line_b": None})
    for key in only_b_keys:
        i, _ = index_b[key]
        if len(diffs) < MAX_DIFFS:
            diffs.append({"row_id": _row_id(key), "discrepancy_type": "only_in_b",
                          "column_name": None, "value_a": None, "value_b": None,
                          "line_a": None, "line_b": i + 1})

    for key in common:
        ia, row_a = index_a[key]
        ib, row_b = index_b[key]
        row_differs = False
        for col in compare_cols:
            va, vb = str(row_a[col]), str(row_b[col])
            if va != vb:
                row_differs = True
                if len(diffs) < MAX_DIFFS:
                    diffs.append({"row_id": _row_id(key), "discrepancy_type": "value_differs",
                                  "column_name": col, "value_a": va[:500], "value_b": vb[:500],
                                  "line_a": ia + 1, "line_b": ib + 1})
        if row_differs:
            differing += 1

    total = max(len(df_a), len(df_b))
    matched = len(common) - differing
    return {
        "elements_a": int(len(df_a)), "elements_b": int(len(df_b)),
        "only_in_a": len(only_a_keys), "only_in_b": len(only_b_keys), "differing": differing,
        "match_percent": round(matched / total * 100, 2) if total else 100.0,
        "diffs": diffs,
    }


# --------------------------------------------------------------------------- #
# Orquestador
# --------------------------------------------------------------------------- #
def _aggregate(sections: dict[str, dict]) -> dict:
    agg = {"elements_a": 0, "elements_b": 0, "only_in_a": 0, "only_in_b": 0, "differing": 0}
    for s in sections.values():
        for k in agg:
            agg[k] += s.get(k, 0)
    total = max(agg["elements_a"], agg["elements_b"])
    matched = total - (agg["only_in_a"] + agg["only_in_b"] + agg["differing"])
    agg["match_percent"] = round(max(matched, 0) / total * 100, 2) if total else 100.0
    return agg


def compare_interfaces(
    file_a: str | Path,
    file_b: str | Path,
    layout_name: str,
    mode: str = "by_id",
    key_columns: list[str] | None = None,
) -> dict:
    """
    Compara dos archivos de la misma interfaz y devuelve el documento consolidado.

    Args:
        mode: 'by_id' (por columnas clave, por sección) o 'by_line' (línea a línea).
        key_columns: columnas clave para 'by_id'. Si es None, se usa el
            `key_columns` del layout; si tampoco hay, se compara posicionalmente.
    """
    file_a, file_b = Path(file_a), Path(file_b)
    layout = load_layout(layout_name)
    interface = layout.get("interface", "UNKNOWN")
    keys = key_columns or layout.get("key_columns")

    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    if mode == "by_line":
        sections = {"whole_file": compare_by_line(file_a, file_b)}
    elif mode == "by_id":
        parser = make_parser(layout)
        parsed_a = parser.parse_file(file_a)
        parsed_b = parser.parse_file(file_b)
        sections = {}
        for section, df_a in parsed_a.sections.items():
            df_b = parsed_b.sections.get(section, df_a.iloc[0:0])
            sections[section] = compare_section(df_a, df_b, keys)
    else:
        raise ValueError(f"Modo de comparación no soportado: {mode}")

    finished = datetime.now(timezone.utc)
    summary = _aggregate(sections)

    return {
        "interface": interface,
        "layout": layout_name,
        "mode": mode,
        "key_columns": keys if mode == "by_id" else None,
        "file_a": file_a.name,
        "file_b": file_b.name,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_ms": int((time.perf_counter() - t0) * 1000),
        "summary": summary,
        "sections": sections,
    }
