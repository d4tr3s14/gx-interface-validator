"""Capa de persistencia: carga validaciones y comparaciones en PostgreSQL."""
from .etl import CatalogError, load_comparison, load_document

__all__ = ["load_document", "load_comparison", "CatalogError"]
