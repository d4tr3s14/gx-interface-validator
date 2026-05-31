"""Consolida los resultados de todas las secciones en un único JSON por interfaz."""
from .merge import consolidate, write_consolidated

__all__ = ["consolidate", "write_consolidated"]
