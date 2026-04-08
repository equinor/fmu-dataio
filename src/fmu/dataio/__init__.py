"""Top-level package for fmu-dataio"""

from fmu.dataio.dataio import ExportData, read_metadata
from fmu.dataio.exceptions import (
    ConfigurationError,
    DeprecationError,
    InvalidMetadataError,
    ValidationError,
)
from fmu.dataio.preprocessed import ExportPreprocessedData

try:
    from .version import version

    __version__ = version
except ImportError:
    __version__ = "0.0.0"

__all__ = [
    "ConfigurationError",
    "DeprecationError",
    "ExportData",
    "ExportPreprocessedData",
    "InvalidMetadataError",
    "ValidationError",
    "read_metadata",
]
