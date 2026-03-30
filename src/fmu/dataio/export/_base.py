from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final

from fmu.dataio._global_config import load_global_config
from fmu.dataio._logging import null_logger
from fmu.dataio.export._export_result import ExportResult

if TYPE_CHECKING:
    from fmu.dataio.export._export_result import ExportResult


logger: Final = null_logger(__name__)


class SimpleExportBase(ABC):
    """Base class for simple export classes."""

    def __init__(self) -> None:
        self._config = load_global_config(standard_result=True)
        logger.debug("SimpleExportBase class initialized")

    @abstractmethod
    def _export_data_as_standard_result(self) -> ExportResult:
        """Export the data as standard result"""
        raise NotImplementedError

    @abstractmethod
    def _validate_data_pre_export(self) -> None:
        """Data validation prior to export"""
        raise NotImplementedError

    def export(self) -> ExportResult:
        """Validate the data and export to disk as a standard_result."""
        self._validate_data_pre_export()
        return self._export_data_as_standard_result()
