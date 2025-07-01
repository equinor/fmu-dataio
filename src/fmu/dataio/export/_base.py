from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pydantic

from fmu.dataio._logging import null_logger
from fmu.dataio._utils import load_config_from_path
from fmu.dataio.exceptions import ValidationError
from fmu.dataio.export._export_result import ExportResult
from fmu.datamodels.fmu_results.enums import Content
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

if TYPE_CHECKING:
    from fmu.dataio.export._export_result import ExportResult
    from fmu.datamodels.fmu_results.enums import Classification
    from fmu.datamodels.fmu_results.standard_result import StandardResult

logger: Final = null_logger(__name__)


class SimpleExportBase(ABC):
    """Base class for simple export classes."""

    def __init__(self, config_path: Path) -> None:
        self._config = self._load_global_config(config_path)
        logger.debug("SimpleExportBase class initialized")

    @property
    @abstractmethod
    def _standard_result(self) -> StandardResult:
        """Standard result class for the exported data."""
        raise NotImplementedError

    @property
    @abstractmethod
    def _content(self) -> Content:
        """Content for the exported data."""
        raise NotImplementedError

    @property
    @abstractmethod
    def _classification(self) -> Classification:
        """Access classification for the exported data."""
        raise NotImplementedError

    @property
    @abstractmethod
    def _rep_include(self) -> bool:
        """rep_include status for the exported data."""
        raise NotImplementedError

    @property
    def _subfolder(self) -> str:
        """Subfolder used for the exported data, equal to the standard result name."""
        return self._standard_result.name.value

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

    def _load_global_config(self, config_path: Path) -> GlobalConfiguration:
        """Load the global config from standard path and return validated config."""
        if not config_path.exists():
            raise FileNotFoundError(
                "Could not detect the global config file at standard "
                f"location: {config_path}."
            )
        config = load_config_from_path(config_path)
        return self._validate_global_config(config)

    @staticmethod
    def _validate_global_config(config: dict[str, Any]) -> GlobalConfiguration:
        """Validate the input config using pydantic, raise error if invalid."""
        try:
            return GlobalConfiguration.model_validate(config)
        except pydantic.ValidationError as err:
            error_message = (
                "When exporting standard_results it is required "
                "to have a valid config.\n"
            )
            if "masterdata" not in config:
                error_message += (
                    "Follow the 'Getting started' steps to do necessary preparations: "
                    "https://fmu-dataio.readthedocs.io/en/latest/preparations.html "
                )

            raise ValidationError(
                f"{error_message}\nDetailed information: \n{err}"
            ) from err
