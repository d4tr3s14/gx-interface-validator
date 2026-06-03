"""
Parsers de interfaces guiados por un layout YAML.

Dos formatos soportados (según `format` en el layout):
  * fixed_width  -> ancho fijo por posiciones (start/length)        [por defecto]
  * delimited    -> delimitado por un separador (",", ";", "|", "\\t", ...)

Ambos producen lo mismo: tres DataFrames (header / body / footer), con los
valores como texto para no perder ceros a la izquierda ni espacios.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

SECTIONS = ("header", "body", "footer")


def load_layout(source: str | Path) -> dict:
    """Carga un layout desde una ruta a YAML o desde el nombre de un layout interno."""
    from interface_validator.layouts import layout_path

    path = Path(source)
    if not path.exists():
        path = layout_path(str(source))
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class ParsedInterface:
    """Resultado de parsear una interfaz: un DataFrame por sección."""

    interface: str
    file_name: str
    sections: dict[str, pd.DataFrame] = field(default_factory=dict)

    def __getitem__(self, section: str) -> pd.DataFrame:
        return self.sections[section]


class FixedWidthParser:
    """Parsea archivos de ancho fijo según un layout de interfaz."""

    def __init__(self, layout: dict):
        self.layout = layout
        self.interface = layout.get("interface", "UNKNOWN")
        self.record_types = layout["record_types"]

    # ------------------------------------------------------------------ #
    # Clasificación de líneas
    # ------------------------------------------------------------------ #
    def _matches_marker(self, line: str, section: str) -> bool:
        marker = self.record_types.get(section, {}).get("marker")
        if not marker:
            return False
        start = marker["start"] - 1
        end = start + marker["length"]
        return line[start:end] == marker["value"]

    def classify(self, line: str) -> Optional[str]:
        """Devuelve 'header', 'footer' o 'body' según el marcador de la línea."""
        for section in ("header", "footer"):
            if self._matches_marker(line, section):
                return section
        # body solo si está definido en el layout
        return "body" if "body" in self.record_types else None

    # ------------------------------------------------------------------ #
    # Corte por posiciones fijas
    # ------------------------------------------------------------------ #
    def _slice_row(self, line: str, columns: list[dict]) -> dict[str, str]:
        row = {}
        for col in columns:
            start = col["start"] - 1
            end = start + col["length"]
            # No se aplica strip: se preservan espacios y ceros significativos.
            row[col["name"]] = line[start:end]
        return row

    def parse_lines(self, lines: list[str]) -> dict[str, list[dict]]:
        buckets: dict[str, list[dict]] = {s: [] for s in SECTIONS}
        for raw in lines:
            line = raw.rstrip("\r\n")
            if not line:
                continue
            section = self.classify(line)
            if section is None:
                continue
            columns = self.record_types[section]["columns"]
            buckets[section].append(self._slice_row(line, columns))
        return buckets

    def parse_file(self, fc_path: str | Path) -> ParsedInterface:
        """Parsea un archivo `.FC` completo y devuelve un :class:`ParsedInterface`."""
        fc_path = Path(fc_path)
        with open(fc_path, "r", encoding="latin-1") as f:
            lines = f.readlines()

        buckets = self.parse_lines(lines)
        sections: dict[str, pd.DataFrame] = {}
        for section, rows in buckets.items():
            columns = [c["name"] for c in self.record_types[section]["columns"]]
            sections[section] = pd.DataFrame(rows, columns=columns, dtype="string")

        return ParsedInterface(
            interface=self.interface,
            file_name=fc_path.name,
            sections=sections,
        )


def _column_names(columns: list) -> list[str]:
    """Nombres de columna: acepta lista de strings o de dicts {name,...}."""
    return [c if isinstance(c, str) else c["name"] for c in columns]


_DELIMITER_ALIASES = {"\\t": "\t", "tab": "\t", "TAB": "\t"}


class DelimitedParser:
    """Parsea archivos delimitados (CSV-like) según un layout de interfaz."""

    def __init__(self, layout: dict):
        self.layout = layout
        self.interface = layout.get("interface", "UNKNOWN")
        self.record_types = layout["record_types"]
        delim = layout.get("delimiter", ",")
        self.delimiter = _DELIMITER_ALIASES.get(delim, delim)

    def _matches_marker(self, fields: list[str], section: str) -> bool:
        marker = self.record_types.get(section, {}).get("marker")
        if not marker:
            return False
        idx = marker["field"]
        return len(fields) > idx and fields[idx].strip() == marker["value"]

    def classify(self, fields: list[str]) -> Optional[str]:
        for section in ("header", "footer"):
            if self._matches_marker(fields, section):
                return section
        return "body" if "body" in self.record_types else None

    def parse_file(self, fc_path: str | Path) -> ParsedInterface:
        fc_path = Path(fc_path)
        buckets: dict[str, list[dict]] = {s: [] for s in SECTIONS}

        with open(fc_path, "r", encoding="latin-1", newline="") as f:
            for fields in csv.reader(f, delimiter=self.delimiter):
                if not fields:
                    continue
                section = self.classify(fields)
                if section is None:
                    continue
                names = _column_names(self.record_types[section]["columns"])
                buckets[section].append(
                    {name: (fields[i] if i < len(fields) else "") for i, name in enumerate(names)}
                )

        sections: dict[str, pd.DataFrame] = {}
        for section, rows in buckets.items():
            names = _column_names(self.record_types.get(section, {}).get("columns", []))
            sections[section] = pd.DataFrame(rows, columns=names, dtype="string")

        return ParsedInterface(interface=self.interface, file_name=fc_path.name, sections=sections)


def make_parser(layout: dict):
    """Devuelve el parser adecuado según el formato del layout."""
    fmt = layout.get("format", "fixed_width")
    if fmt == "delimited" or layout.get("delimiter"):
        return DelimitedParser(layout)
    return FixedWidthParser(layout)


def parse_interface(fc_path: str | Path, layout_name: str) -> ParsedInterface:
    """Atajo: carga el layout por nombre y parsea el archivo."""
    layout = load_layout(layout_name)
    return make_parser(layout).parse_file(fc_path)
