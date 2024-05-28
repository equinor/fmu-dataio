from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pandas as pd

from fmu.dataio._definitions import STANDARD_TABLE_INDEX_COLUMNS, ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio.datastructure.meta.enums import FMUClassEnum
from fmu.dataio.datastructure.meta.specification import TableSpecification

from ._base import (
    DerivedObjectDescriptor,
    ObjectDataProvider,
)

if TYPE_CHECKING:
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
    def classname(self) -> FMUClassEnum:
        return FMUClassEnum.table

    def get_spec(self) -> TableSpecification:
        """Derive data.spec for pd.DataFrame."""
        logger.info("Get spec for pd.DataFrame (tables)")
        return TableSpecification(
            columns=list(self.obj.columns),
            size=int(self.obj.size),
        )

    def get_bbox(self) -> None:
        """Derive data.bbox for pd.DataFrame."""

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for pd.DataFrame."""
        table_index = _derive_index(self.dataio.table_index, list(self.obj.columns))
        return DerivedObjectDescriptor(
            subtype="DataFrame",
            layout="table",
            efolder="tables",
            fmt=(fmt := self.dataio.table_fformat),
            extension=self._validate_get_ext(fmt, "DataFrame", ValidFormats().table),
            table_index=table_index,
        )


@dataclass
class ArrowTableDataProvider(ObjectDataProvider):
    obj: pyarrow.Table

    @property
    def classname(self) -> FMUClassEnum:
        return FMUClassEnum.table

    def get_spec(self) -> TableSpecification:
        """Derive data.spec for pyarrow.Table."""
        logger.info("Get spec for pyarrow (tables)")
        return TableSpecification(
            columns=list(self.obj.column_names),
            size=self.obj.num_columns * self.obj.num_rows,
        )

    def get_bbox(self) -> None:
        """Derive data.bbox for pyarrow.Table."""

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data from pyarrow.Table."""
        table_index = _derive_index(self.dataio.table_index, self.obj.column_names)
        return DerivedObjectDescriptor(
            subtype="ArrowTable",
            layout="table",
            efolder="tables",
            fmt=(fmt := self.dataio.arrow_fformat),
            extension=self._validate_get_ext(fmt, "ArrowTable", ValidFormats().table),
            table_index=table_index,
        )
