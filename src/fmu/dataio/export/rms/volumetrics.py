from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final
from warnings import warn

import pandas as pd
from packaging.version import parse as versionparse

import fmu.dataio as dio
from fmu.config.utilities import yaml_load
from fmu.dataio._logging import null_logger

from .._decorators import experimental
from ._conditional_rms_imports import import_rms_package

_modules = import_rms_package()
if _modules:
    rmsapi = _modules["rmsapi"]
    jobs = _modules["jobs"]


_logger: Final = null_logger(__name__)

# rename columns to FMU standard
_RENAME_COLUMNS_FROM_RMS: Final = {
    "Proj. real.": "REAL",
    "Zone": "ZONE",
    "Segment": "REGION",
    "Boundary": "LICENSE",
    "Facies": "FACIES",
    "BulkOil": "BULK_OIL",
    "NetOil": "NET_OIL",
    "PoreOil": "PORV_OIL",
    "HCPVOil": "HCPV_OIL",
    "STOIIP": "STOIIP_OIL",
    "AssociatedGas": "ASSOCIATEDGAS_OIL",
    "BulkGas": "BULK_GAS",
    "NetGas": "NET_GAS",
    "PoreGas": "PORV_GAS",
    "HCPVGas": "HCPV_GAS",
    "GIIP": "GIIP_GAS",
    "AssociatedLiquid": "ASSOCIATEDOIL_GAS",
    "Bulk": "BULK_TOTAL",
    "Net": "NET_TOTAL",
    "Pore": "PORV_TOTAL",
}


@dataclass
class _ExportVolumetricsRMS:
    project: Any
    grid_name: str
    volume_job_name: str

    # optional and defaulted
    global_config: str | Path | dict = "../../fmuconfig/output/global_variables.yml"
    forcefolder: str = ""  # allowed until deprecated
    subfolder: str = ""
    name: str = ""
    tagname: str = "vol"
    classification: str = "restricted"
    workflow: str = "rms volumetric run"

    # internal storage instance variables
    _global_config: dict = field(default_factory=dict, init=False)
    _volume_job: dict = field(default_factory=dict, init=False)
    _volume_table_name: str = field(default="", init=False)
    _dataframe: pd.DataFrame = field(default_factory=pd.DataFrame, init=False)
    _units: str = field(default="metric", init=False)

    def __post_init__(self) -> None:
        _logger.debug("Process data, estiblish state prior to export.")
        self._check_rmsapi_version()
        self._set_global_config()
        self._rms_volume_job_settings()
        self._read_volume_table_name_from_rms()
        self._voltable_as_dataframe()
        self._set_units()
        self._warn_if_forcefolder()
        _logger.debug("Process data... DONE")

    @staticmethod
    def _check_rmsapi_version() -> None:
        """Check if we are working in a RMS API, and also check RMS versions?"""
        _logger.debug("Check API version...")
        if versionparse(rmsapi.__version__) < versionparse("1.7"):
            raise RuntimeError(
                "You need at least API version 1.7 (RMS 13.1) to use this function."
            )
        _logger.debug("Check API version... DONE")

    def _set_global_config(self) -> None:
        """Set the global config data by reading the file."""
        _logger.debug("Set global config...")

        if isinstance(self.global_config, dict):
            self._global_config = self.global_config
            _logger.debug("Set global config (from input dictionary)... DONE!")
            return

        global_config_path = Path(self.global_config)

        if not global_config_path.is_file():
            raise FileNotFoundError(
                f"Cannot find file for global config: {self.global_config}"
            )
        self._global_config = yaml_load(global_config_path)
        _logger.debug("Read config from yaml... DONE")

    def _rms_volume_job_settings(self) -> None:
        """Get information out from the RMS job API."""
        _logger.debug("RMS VOLJOB settings...")
        self._volume_job = jobs.Job.get_job(
            owner=["Grid models", self.grid_name, "Grid"],
            type="Volumetrics",
            name=self.volume_job_name,
        ).get_arguments()
        _logger.debug("RMS VOLJOB settings... DONE")

    def _read_volume_table_name_from_rms(self) -> None:
        """Read the volume table name from RMS."""
        _logger.debug("Read volume table name from RMS...")
        voltable = self._volume_job.get("Report")
        if isinstance(voltable, list):
            voltable = voltable[0]
        self._volume_table_name = voltable.get("ReportTableName")

        if not self._volume_table_name:
            raise RuntimeError(
                "You need to configure output to Report file: Report table "
                "in the volumetric job. Provide a table name and rerun the job."
            )

        _logger.debug("The volume table name is %s", self._volume_table_name)
        _logger.debug("Read volume table name from RMS... DONE")

    def _voltable_as_dataframe(self) -> None:
        """Convert table to pandas dataframe"""
        _logger.debug("Read values and convert to pandas dataframe...")
        dict_values = (
            self.project.volumetric_tables[self._volume_table_name]
            .get_data_table()
            .to_dict()
        )
        _logger.debug("Dict values are: %s", dict_values)
        self._dataframe = pd.DataFrame.from_dict(dict_values)
        self._dataframe.rename(columns=_RENAME_COLUMNS_FROM_RMS, inplace=True)
        self._dataframe.drop("REAL", axis=1, inplace=True, errors="ignore")

        _logger.debug("Read values and convert to pandas dataframe... DONE")

    def _set_units(self) -> None:
        """See if the RMS project is defined in metric or feet."""

        units = self.project.project_units
        _logger.debug("Units are %s", units)
        self._units = str(units)

    def _warn_if_forcefolder(self) -> None:
        if self.forcefolder:
            warn(
                "A 'forcefolder' is set. This is strongly discouraged and will be "
                "removed in coming versions",
                FutureWarning,
            )

    def _export_volume_table(self) -> dict[str, str]:
        """Do the actual volume table export using dataio setup."""

        edata = dio.ExportData(
            config=self._global_config,
            content="volumes",
            unit="m3" if self._units == "metric" else "ft3",
            vertical_domain="depth",
            domain_reference="msl",
            workflow=self.workflow,
            forcefolder=self.forcefolder,
            classification=self.classification,
            tagname=self.tagname,
            name=self.name if self.name else f"{self.grid_name}_volumes",
            rep_include=False,
        )

        out = edata.export(self._dataframe)
        _logger.debug("Volume result to: %s", out)
        return {"volume_table": out}

    def export(self) -> dict[str, str]:
        """Export the volume table."""
        return self._export_volume_table()


@experimental
def export_volumetrics(
    project: Any,
    grid_name: str,
    volume_job_name: str,
    global_config: str | Path | dict = "../../fmuconfig/output/global_variables.yml",
    forcefolder: str = "",  # unsure if we shall allow this?
    subfolder: str = "",
    name: str = "",
    tagname: str = "",
    classification: str = "restricted",
    workflow: str = "rms volumetric run",
) -> dict[str, str]:
    """Simplified interface when exporting volume tables (and assosiated data) from RMS.

    As the export_volumetrics may have multiple output (storing both tables, maps and
    3D grids), the output from this function is always a dictionary. The table is
    mandatory output, while maps and 3D grid data are optional (not yet implemented).

    Args:
        project: The 'magic' project variable in RMS.
        grid_name: Name of 3D grid model in RMS.
        volume_job_name: Name of the volume job.
        global_config: Optional. The global config can either point to the
            global_variables file, or it can be a dictionary. As default, it assumes
            a the current standard in FMU:
            ``'../../fmuconfig/output/global_variables.yml'``
        forcefolder: Optional. As default, volume tables will be exported to the agreed
            file structure, and the folder name will be 'tables'. This can be
            overriden here, but there will be warnings. For optional assosiated
            volume maps and grids, the default folder names cannot be changed.
        subfolder: Name of subfolder for local storage, below the standard folder.
        name: Optional. Name of export item. Is defaulted to name of grid + '_volumes'.
        tagname: Optional. Defaulted to 'vol' for this function. Tagnames are part of
            file names, and should not be applied as metadata.
        classification: Optional. Use 'internal' or 'restricted' (default).
        workflow: Optional. Information about the work flow; defaulted to
            'rms volumetrics'.

    Note:
        This function is experimental and may change in future versions.
    """

    return _ExportVolumetricsRMS(
        project,
        grid_name,
        volume_job_name,
        global_config=global_config,
        forcefolder=forcefolder,
        subfolder=subfolder,
        name=name,
        tagname=tagname,
        classification=classification,
        workflow=workflow,
    ).export()


# keep the old name for now but not log (will be removed soon as we expect close to
# zero usage so far)
def export_rms_volumetrics(*args, **kwargs) -> dict[str, str]:  # type: ignore
    """Deprecated function. Use export_volumetrics instead."""
    warnings.warn(
        "export_rms_volumetrics is deprecated and will be removed in a future release. "
        "Use export_volumetrics instead.",
        FutureWarning,
        stacklevel=2,
    )
    return export_volumetrics(*args, **kwargs)
