"""Subpackage for creating metadata."""

from ._file import FileMetadata, ShareFolder, SharePathConstructor
from ._fmu import ERT_RELATIVE_CASE_METADATA_FILE, FmuMetadata
from ._object import ObjectData, create_object_data
from .core import _generate_metadata, generate_export_metadata, generate_metadata

__all__ = [
    "ERT_RELATIVE_CASE_METADATA_FILE",
    "generate_export_metadata",
    "generate_metadata",
    "_generate_metadata",
    "FileMetadata",
    "SharePathConstructor",
    "ShareFolder",
    "FmuMetadata",
    "ObjectData",
    "create_object_data",
]
