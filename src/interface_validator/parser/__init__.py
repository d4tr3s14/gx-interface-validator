"""Parsers de interfaces (ancho fijo y delimitado) hacia DataFrames por sección."""
from .fixed_width import (
    DelimitedParser,
    FixedWidthParser,
    ParsedInterface,
    load_layout,
    make_parser,
)

__all__ = [
    "FixedWidthParser",
    "DelimitedParser",
    "make_parser",
    "load_layout",
    "ParsedInterface",
]
