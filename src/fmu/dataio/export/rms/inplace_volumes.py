from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd
import pyarrow as pa

import fmu.dataio as dio
from fmu.dataio._logging import null_logger
from fmu.dataio._models import InplaceVolumesResult
from fmu.dataio._models.fmu_results import standard_result
from fmu.dataio._models.fmu_results.enums import Classification, StandardResultName
from fmu.dataio.export import _enums
from fmu.dataio.export._decorators import experimental
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._conditional_rms_imports import import_rms_package
from fmu.dataio.export.rms._utils import (
    check_rmsapi_version,
    get_rms_project_units,
    load_global_config,
)

rmsapi, rmsjobs = import_rms_package()

_logger: Final = null_logger(__name__)


_VolumetricColumns = _enums.InplaceVolumes.VolumetricColumns
_TableIndexColumns = _enums.InplaceVolumes.TableIndexColumns

# rename columns to FMU standard
_RENAME_COLUMNS_FROM_RMS: Final = {
    "Proj. real.": "REAL",
    "Zone": _TableIndexColumns.ZONE.value,
    "Segment": _TableIndexColumns.REGION.value,
    "Boundary": _TableIndexColumns.LICENSE.value,
    "Facies": _TableIndexColumns.FACIES.value,
    "BulkOil": _VolumetricColumns.BULK.value + "_OIL",
    "NetOil": _VolumetricColumns.NET.value + "_OIL",
    "PoreOil": _VolumetricColumns.PORV.value + "_OIL",
    "HCPVOil": _VolumetricColumns.HCPV.value + "_OIL",
    "STOIIP": _VolumetricColumns.STOIIP.value + "_OIL",
    "AssociatedGas": _VolumetricColumns.ASSOCIATEDGAS.value + "_OIL",
    "BulkGas": _VolumetricColumns.BULK.value + "_GAS",
    "NetGas": _VolumetricColumns.NET.value + "_GAS",
    "PoreGas": _VolumetricColumns.PORV.value + "_GAS",
    "HCPVGas": _VolumetricColumns.HCPV.value + "_GAS",
    "GIIP": _VolumetricColumns.GIIP.value + "_GAS",
    "AssociatedLiquid": _VolumetricColumns.ASSOCIATEDOIL.value + "_GAS",
    "Bulk": _VolumetricColumns.BULK.value + "_TOTAL",
    "Net": _VolumetricColumns.NET.value + "_TOTAL",
    "Pore": _VolumetricColumns.PORV.value + "_TOTAL",
}


@dataclass
class _ExportVolumetricsRMS:
    project: Any
    grid_name: str
    volume_job_name: str

    def __post_init__(self) -> None:
        _logger.debug("Process data, establish state prior to export.")
        self._config = load_global_config()
        self._volume_job = self._get_rms_volume_job_settings()
        self._volume_table_name = self._read_volume_table_name_from_job()
        self._dataframe = self._get_table_with_volumes()
        _logger.debug("Process data... DONE")

    @property
    def _standard_result(self) -> standard_result.InplaceVolumesStandardResult:
        """Standard result type for the exported data."""
        return standard_result.InplaceVolumesStandardResult(
            name=StandardResultName.inplace_volumes
        )

    @property
    def _classification(self) -> Classification:
        """Get default classification."""
        return Classification.restricted

    def _get_rms_volume_job_settings(self) -> dict:
        """Get information out from the RMS job API."""
        _logger.debug("RMS VOLJOB settings...")
        return rmsjobs.Job.get_job(
            owner=["Grid models", self.grid_name, "Grid"],
            type="Volumetrics",
            name=self.volume_job_name,
        ).get_arguments()

    def _read_volume_table_name_from_job(self) -> str:
        """Read the volume table name from RMS."""
        _logger.debug("Read volume table name from RMS...")
        voltable = self._volume_job.get("Report")
        if isinstance(voltable, list):
            voltable = voltable[0]

        volume_table_name = voltable.get("ReportTableName")
        if not volume_table_name:
            raise RuntimeError(
                "You need to configure output to Report file: Report table "
                "in the volumetric job. Provide a table name and rerun the job."
            )

        _logger.debug("The volume table name is %s", volume_table_name)
        return volume_table_name

    def _get_table_with_volumes(self) -> pd.DataFrame:
        """
        Get a volumetric table from RMS converted into a pandas
        dataframe on standard format for the inplace_volumes standard result.
        """
        table = self._get_table_from_rms()
        table = self._convert_table_from_rms_to_legacy_format(table)
        return self._convert_table_from_legacy_to_standard_format(table)

    def _get_table_from_rms(self) -> pd.DataFrame:
        """Fetch volumetric table from RMS and convert to pandas dataframe"""
        _logger.debug("Read values and convert to pandas dataframe...")
        return pd.DataFrame.from_dict(
            self.project.volumetric_tables[self._volume_table_name]
            .get_data_table()
            .to_dict()
        )

    @staticmethod
    def _convert_table_from_rms_to_legacy_format(table: pd.DataFrame) -> pd.DataFrame:
        """Rename columns to legacy naming standard and drop REAL column if present."""
        _logger.debug("Converting dataframe from RMS to legacy format...")
        return table.rename(columns=_RENAME_COLUMNS_FROM_RMS).drop(
            columns="REAL", errors="ignore"
        )

    @staticmethod
    def _compute_water_zone_volumes_from_totals(table: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate 'water' zone volumes by subtracting HC-zone volumes from 'Total'
        volumes which represents the entire zone. Total volumes are removed after
        'water' zone volumes have been added to the table.
        """
        _logger.debug("Computing water volumes from Totals...")

        total_suffix = "_TOTAL"
        total_columns = [col for col in table.columns if col.endswith(total_suffix)]

        if not total_columns:
            raise RuntimeError(
                "Found no 'Totals' volumes in the table. Please ensure 'Totals' "
                "are reported and rerun the volumetric job before export."
            )

        for total_col in total_columns:
            volumetric_col = total_col.replace(total_suffix, "")

            water_zone_col = f"{volumetric_col}_WATER"
            oil_zone_col = f"{volumetric_col}_OIL"
            gas_zone_col = f"{volumetric_col}_GAS"

            # first set water zone data equal to the Total
            # then subtract data from the oil/gas zone
            table[water_zone_col] = table[total_col]

            if oil_zone_col in table:
                table[water_zone_col] -= table[oil_zone_col]

            if gas_zone_col in table:
                table[water_zone_col] -= table[gas_zone_col]

        return table.drop(columns=total_columns)

    @staticmethod
    def _add_missing_columns_to_table(table: pd.DataFrame) -> pd.DataFrame:
        """Add columns with nan values if not present in table."""
        _logger.debug("Add table index columns to table if missing...")
        for col in _enums.InplaceVolumes.table_columns():
            if col not in table:
                table[col] = np.nan
        return table

    @staticmethod
    def _set_net_equal_to_bulk_if_missing_in_table(table: pd.DataFrame) -> pd.DataFrame:
        """
        Add a NET column to the table equal to the BULK column if NET is missing,
        since the absence implies a net-to-gross ratio of 1.
        """
        if _VolumetricColumns.NET.value not in table:
            _logger.debug("NET column missing, setting NET equal BULK...")
            table[_VolumetricColumns.NET.value] = table[_VolumetricColumns.BULK.value]
        return table

    @staticmethod
    def _set_table_column_order(table: pd.DataFrame) -> pd.DataFrame:
        """Set the column order in the table."""
        _logger.debug("Settting the table column order...")
        return table[_enums.InplaceVolumes.table_columns()]

    @staticmethod
    def _transform_and_add_fluid_column_to_table(
        table: pd.DataFrame, table_index: list[str]
    ) -> pd.DataFrame:
        """
        Transformation of a dataframe containing fluid-specific column data into a
        standardized format with unified column names, e.g. 'BULK_OIL' and 'PORV_OIL'
        are renamed into 'BULK' and 'PORV' columns. To separate the data an additional
        FLUID column is added that indicates the type of fluid the row represents.
        """

        tables = []
        for fluid in (
            _enums.InplaceVolumes.Fluid.gas.value,
            _enums.InplaceVolumes.Fluid.oil.value,
            _enums.InplaceVolumes.Fluid.water.value,
        ):
            fluid_suffix = fluid.upper()
            fluid_columns = [
                col for col in table.columns if col.endswith(f"_{fluid_suffix}")
            ]
            if fluid_columns:
                fluid_table = table[table_index + fluid_columns].copy()

                # drop fluid suffix from columns to get standard names
                fluid_table.columns = fluid_table.columns.str.replace(
                    f"_{fluid_suffix}", ""
                )

                # add the fluid as column entry instead
                fluid_table[_TableIndexColumns.FLUID.value] = fluid

                tables.append(fluid_table)

        return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()

    def _convert_table_from_legacy_to_standard_format(
        self, table: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Convert the table from legacy to standard format for the 'inplace_volumes'
        standard result. The standard format has a fluid column, and all table_index
        and volumetric columns are present with a standard order in the table.
        """
        table_index = [
            col for col in _enums.InplaceVolumes.index_columns() if col in table
        ]
        table = self._compute_water_zone_volumes_from_totals(table)
        table = self._transform_and_add_fluid_column_to_table(table, table_index)
        table = self._set_net_equal_to_bulk_if_missing_in_table(table)
        table = self._add_missing_columns_to_table(table)
        return self._set_table_column_order(table)

    def _is_column_missing_in_table(self, column: str) -> bool:
        """Check if a column is present in the final dataframe and has values"""
        return column not in self._dataframe or self._dataframe[column].isna().all()

    def _validate_table(self) -> None:
        """
        Validate that the final table with volumes is according to the standard
        defined for the inplace_volumes standard result. The table should have the
        required index and value columns, and at least one of the main types 'oil' or
        'gas'.
        """
        _logger.debug("Validating the dataframe...")

        # check that all required index columns are present
        for col in _enums.InplaceVolumes.required_index_columns():
            if self._is_column_missing_in_table(col):
                raise RuntimeError(
                    f"Required index column {col} is missing in the volumetric table. "
                    "Please update and rerun the volumetric job before export."
                )

        has_oil = "oil" in self._dataframe[_TableIndexColumns.FLUID.value].values
        has_gas = "gas" in self._dataframe[_TableIndexColumns.FLUID.value].values

        # check that one of oil and gas fluids are present
        if not (has_oil or has_gas):
            raise RuntimeError(
                "One or both 'oil' and 'gas' needs to be selected as 'Main types'"
                "in the volumetric job. Please update and rerun the volumetric job "
                "before export."
            )

        # check that all required value columns are present
        missing_calculations = []
        for col in _enums.InplaceVolumes.required_value_columns():
            if self._is_column_missing_in_table(col):
                missing_calculations.append(col)

        if has_oil and self._is_column_missing_in_table(
            _VolumetricColumns.STOIIP.value
        ):
            missing_calculations.append(_VolumetricColumns.STOIIP.value)

        if has_gas and self._is_column_missing_in_table(_VolumetricColumns.GIIP.value):
            missing_calculations.append(_VolumetricColumns.GIIP.value)

        if missing_calculations:
            raise RuntimeError(
                f"Required calculations {missing_calculations} are missing "
                f"in the volumetric table {self._volume_table_name}. Please update and "
                "rerun the volumetric job before export."
            )

        df = self._dataframe.replace(np.nan, None).to_dict(orient="records")
        InplaceVolumesResult.model_validate(df)

    def _export_volume_table(self) -> ExportResult:
        """Do the actual volume table export using dataio setup."""

        edata = dio.ExportData(
            config=self._config,
            content="volumes",
            unit="m3" if get_rms_project_units(self.project) == "metric" else "ft3",
            vertical_domain="depth",
            domain_reference="msl",
            subfolder="volumes",
            classification=self._classification,
            name=self.grid_name,
            rep_include=False,
            table_index=_enums.InplaceVolumes.index_columns(),
        )

        volume_table = pa.Table.from_pandas(self._dataframe)

        # export the volume table with standard result info in the metadata
        absolute_export_path = edata._export_with_standard_result(
            volume_table,
            standard_result=self._standard_result,
        )

        _logger.debug("Volume result to: %s", absolute_export_path)
        return ExportResult(
            items=[
                ExportResultItem(
                    absolute_path=Path(absolute_export_path),
                )
            ],
        )

    def export(self) -> ExportResult:
        """Validate and export the volume table."""
        self._validate_table()
        return self._export_volume_table()


@experimental
def export_inplace_volumes(
    project: Any,
    grid_name: str,
    volume_job_name: str,
) -> ExportResult:
    """Simplified interface when exporting volume tables (and assosiated data) from RMS.

    Args:
        project: The 'magic' project variable in RMS.
        grid_name: Name of 3D grid model in RMS.
        volume_job_name: Name of the volume job.

    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_inplace_volumes

            export_results = export_inplace_volumes(project, "Geogrid", "geogrid_volumes")

            for result in export_results.items:
                print(f"Output volumes to {result.absolute_path}")

    """  # noqa: E501 line too long

    check_rmsapi_version(minimum_version="1.7")

    return _ExportVolumetricsRMS(
        project,
        grid_name,
        volume_job_name,
    ).export()


# keep the old name for now but not log (will be removed soon as we expect close to
# zero usage so far)
def export_rms_volumetrics(*args, **kwargs) -> ExportResult:  # type: ignore
    """Deprecated function. Use export_inplace_volumes instead."""
    warnings.warn(
        "export_rms_volumetrics is deprecated and will be removed in a future release. "
        "Use export_inplace_volumes instead.",
        FutureWarning,
        stacklevel=2,
    )
    return export_inplace_volumes(*args, **kwargs)
