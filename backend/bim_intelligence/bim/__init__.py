"""IFC loading and the Model Index (ARCHITECTURE §8).

This package and ``validation/`` are the only ones that import ``ifcopenshell`` (AGENTS.md §3).
"""

from bim_intelligence.bim.errors import (
    AmbiguousGlobalIdError,
    IfcLoadError,
    InvalidGlobalIdError,
    UnknownElementError,
    UnsupportedSchemaError,
    UnsupportedUploadError,
)
from bim_intelligence.bim.indexer import build_index
from bim_intelligence.bim.ingest import ingest_model, load_index, load_summary
from bim_intelligence.bim.loader import SUPPORTED_SCHEMAS, open_ifc
from bim_intelligence.bim.model_index import ModelIndex

__all__ = [
    "SUPPORTED_SCHEMAS",
    "AmbiguousGlobalIdError",
    "IfcLoadError",
    "InvalidGlobalIdError",
    "ModelIndex",
    "UnknownElementError",
    "UnsupportedSchemaError",
    "UnsupportedUploadError",
    "build_index",
    "ingest_model",
    "load_index",
    "load_summary",
    "open_ifc",
]
