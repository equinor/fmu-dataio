from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from fmu.dataio._definitions import (
    STANDARD_TABLE_INDEX_COLUMNS,
    ExportFolder,
    ValidFormats,
)
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.enums import Content, FileFormat, FMUClass, Layout
from fmu.dataio._models.fmu_results.specification import TableSpecification

from ._base import (
    ObjectDataProvider,
)

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow

logger: Final = null_logger(__name__)


def _validate_input_table_index(
    table_index: list[str],
    table_columns: list[str],
    content: Content | None = None,
) -> None:
    """
    Check that all provided table index columns are present in the table, and warn if
    non-standard table indexes are used or some standard ones are missing.
    """

    missing_columns = [col for col in table_index if col not in table_columns]
    if missing_columns:
        raise KeyError(
            f"The table index columns {missing_columns} are not present in the table"
        )

    if content in STANDARD_TABLE_INDEX_COLUMNS:
        standard_required_index = STANDARD_TABLE_INDEX_COLUMNS[content].required
        if set(standard_required_index) != set(table_index):
            warnings.warn(
                "The table index provided deviates from the standard: "
                f"{standard_required_index}. This may not be allowed in the future.",
                FutureWarning,
            )


def _derive_index_from_standard(
    content: Content, table_columns: list[str]
) -> list[str]:
    """
    Derive standard table index for given content. Give warning if some
    standard required index columns are missing in the table.
    """
    logger.debug("Using standard table_index for content %s", content.value)
    standard_index = STANDARD_TABLE_INDEX_COLUMNS[content]

    table_index = [col for col in standard_index.columns if col in table_columns]
    if not table_index:
        warnings.warn(
            "Could not detect any standard index columns in table: "
            f"{standard_index.columns}. If the table has index columns they "
            "should be provided as input through the 'table_index' argument."
        )
    elif set(standard_index.required) != set(table_index):
        warnings.warn(
            "The table provided does not contain all required standard "
            f"table index columns for this content: {standard_index.required}. "
            "This may not be allowed in the future.",
            FutureWarning,
        )
    return table_index


def _derive_index_legacy(table_columns: list[str]) -> list[str]:
    """
    Derive all columns in table that is registered as a standard index column,
    independent of the content.
    """
    table_index = []
    for standard_table_index in STANDARD_TABLE_INDEX_COLUMNS.values():
        for col in standard_table_index.columns:
            if col in table_columns and col not in table_index:
                table_index.append(col)
    return table_index


def _derive_index(
    table_columns: list[str],
    table_index: list[str] | None,
    content: Content | None = None,
) -> list[str]:
    """
    Derive the index for a table based on a provided table_index or using
    standard index columns for the specific content.

    If no table index is provided and content is not registered with any standard table
    indexes, the index is set using the legacy method; columns in table that
    matches any registered standard index columns (independent of content).
    """
    if table_index:
        logger.debug("Table index provided, validating input...")
        _validate_input_table_index(table_index, table_columns, content)
        return table_index

    logger.debug("No table index provided")

    if content in STANDARD_TABLE_INDEX_COLUMNS:
        table_index = _derive_index_from_standard(content, table_columns)
    else:
        table_index = _derive_index_legacy(table_columns)
        if table_index:
            warnings.warn(
                "The 'table_index' was not provided, and has been set based upon "
                "commonly known table index columns found in the table: "
                f"{table_index}. In the future the table_index will be empty in the "
                "metadata if not provided as input through the 'table_index' argument.",
                FutureWarning,
            )
    # TODO: Look into removing this, probably only applicable for aggregated data.
    if "REAL" in table_columns and "REAL" not in table_index:
        table_index.append("REAL")

    logger.debug("Final table_index is %s", table_index)
    return table_index


@dataclass
class DataFrameDataProvider(ObjectDataProvider):
    obj: pd.DataFrame

    @property
    def classname(self) -> FMUClass:
        return FMUClass.table

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.tables.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt.value, ValidFormats.table)

    @property
    def fmt(self) -> FileFormat:
        return FileFormat(self.dataio.table_fformat)

    @property
    def layout(self) -> Layout:
        return Layout.table

    @property
    def table_index(self) -> list[str]:
        """Return the table index."""
        return _derive_index(
            table_index=self.dataio.table_index,
            table_columns=list(self.obj.columns),
            content=self.dataio._get_content_enum(),
        )

    def get_geometry(self) -> None:
        """Derive data.geometry for data frame"""

    def get_bbox(self) -> None:
        """Derive data.bbox for pd.DataFrame."""

    def get_spec(self) -> TableSpecification:
        """Derive data.spec for pd.DataFrame."""
        logger.info("Get spec for pd.DataFrame (tables)")
        num_rows, num_columns = self.obj.shape
        return TableSpecification(
            columns=list(self.obj.columns),
            num_columns=num_columns,
            num_rows=num_rows,
            size=int(self.obj.size),
        )


@dataclass
class ArrowTableDataProvider(ObjectDataProvider):
    obj: pyarrow.Table

    @property
    def classname(self) -> FMUClass:
        return FMUClass.table

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.tables.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt.value, ValidFormats.table)

    @property
    def fmt(self) -> FileFormat:
        return FileFormat(self.dataio.arrow_fformat)

    @property
    def layout(self) -> Layout:
        return Layout.table

    @property
    def table_index(self) -> list[str]:
        """Return the table index."""
        return _derive_index(
            table_index=self.dataio.table_index,
            table_columns=list(self.obj.column_names),
            content=self.dataio._get_content_enum(),
        )

    def get_geometry(self) -> None:
        """Derive data.geometry for Arrow table."""

    def get_bbox(self) -> None:
        """Derive data.bbox for pyarrow.Table."""

    def get_spec(self) -> TableSpecification:
        """Derive data.spec for pyarrow.Table."""
        logger.info("Get spec for pyarrow (tables)")
        return TableSpecification(
            columns=list(self.obj.column_names),
            num_columns=self.obj.num_columns,
            num_rows=self.obj.num_rows,
            size=self.obj.num_columns * self.obj.num_rows,
        )
