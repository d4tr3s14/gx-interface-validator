"""Capa de persistencia: carga los resultados de validación en PostgreSQL."""
from .etl import CatalogError, load_document

__all__ = ["load_document", "CatalogError"]
