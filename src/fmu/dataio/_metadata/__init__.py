"""Subpackage for creating metadata."""

from ._filedata import FileDataProvider, ShareFolder, SharePathConstructor
from ._fmu import ERT_RELATIVE_CASE_METADATA_FILE, FmuProvider
from .core import _generate_metadata, generate_export_metadata, generate_metadata
from .objectdata import ObjectDataProvider, objectdata_provider_factory

__all__ = [
    "ERT_RELATIVE_CASE_METADATA_FILE",
    "generate_export_metadata",
    "generate_metadata",
    "_generate_metadata",
    "FileDataProvider",
    "SharePathConstructor",
    "ShareFolder",
    "FmuProvider",
    "ObjectDataProvider",
    "objectdata_provider_factory",
]
