"""Parser de archivos de ancho fijo (.FC) hacia DataFrames por sección."""
from .fixed_width import FixedWidthParser, load_layout, ParsedInterface

__all__ = ["FixedWidthParser", "load_layout", "ParsedInterface"]
