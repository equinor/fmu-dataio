from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from fmu.dataio._definitions import (
    STANDARD_TABLE_INDEX_COLUMNS,
    ExportFolder,
    ValidFormats,
)
from fmu.dataio._logging import null_logger
from fmu.dataio._model.enums import FMUClass, Layout
from fmu.dataio._model.specification import TableSpecification

from ._base import (
    ObjectDataProvider,
)

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow

logger: Final = null_logger(__name__)


def _check_index_in_columns(index: list[str], columns: list[str]) -> None:
    """Check the table index.
    Args:
        index (list): list of column names

    Raises:
        KeyError: if index contains names that are not in self
    """

    not_founds = (item for item in index if item not in columns)
    for not_found in not_founds:
        raise KeyError(f"{not_found} is not in table")


def _derive_index(table_index: list[str] | None, columns: list[str]) -> list[str]:
    index = []

    if table_index is None:
        logger.debug("Finding index to include")
        for context, standard_cols in STANDARD_TABLE_INDEX_COLUMNS.items():
            for valid_col in standard_cols:
                if valid_col in columns:
                    index.append(valid_col)
            if index:
                logger.info("Context is %s ", context)
        logger.debug("Proudly presenting the index: %s", index)
    else:
        index = table_index

    if "REAL" in columns:
        index.append("REAL")
    _check_index_in_columns(index, columns)
    return index


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
        return self._validate_get_ext(self.fmt, ValidFormats.table)

    @property
    def fmt(self) -> str:
        return self.dataio.table_fformat

    @property
    def layout(self) -> Layout:
        return Layout.table

    @property
    def table_index(self) -> list[str]:
        """Return the table index."""
        return _derive_index(self.dataio.table_index, list(self.obj.columns))

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
        return self._validate_get_ext(self.fmt, ValidFormats.table)

    @property
    def fmt(self) -> str:
        return self.dataio.arrow_fformat

    @property
    def layout(self) -> Layout:
        return Layout.table

    @property
    def table_index(self) -> list[str]:
        """Return the table index."""
        return _derive_index(self.dataio.table_index, list(self.obj.column_names))

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
