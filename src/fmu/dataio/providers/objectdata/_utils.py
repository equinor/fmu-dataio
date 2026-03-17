from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from fmu.datamodels.fmu_results.specification import Statistics

if TYPE_CHECKING:
    import pandas as pd

    from fmu.datamodels.fmu_results.global_configuration import Stratigraphy


class Utils:
    @staticmethod
    def get_stratigraphic_name(stratigraphy: Stratigraphy, name: str) -> str:
        """
        Get the name of a stratigraphic element from the stratigraphy.
        name: name of stratigraphic element
        """
        if name in stratigraphy:
            return stratigraphy[name].name

        warnings.warn(
            f"Stratigraphic element '{name}' not found in the stratigraphic column "
            "in global config"
        )
        return ""


def is_empty_column_pandas(table: pd.DataFrame, column: str) -> bool:
    """Check if a column in the table is empty (all values are NaN or null)."""
    return bool(table[column].isna().all())


def is_empty_column_pyarrow(table: pa.Table, column: str) -> bool:
    """Check if a column in the table is empty (all values are NaN or null)."""
    return pc.all(table[column].is_null()).as_py()


def is_empty_column(table: pd.DataFrame | pa.Table, column: str) -> bool:
    """Check if a column in the table is empty (all values are NaN or null)."""

    if isinstance(table, pa.Table):
        return is_empty_column_pyarrow(table, column)
    return is_empty_column_pandas(table, column)


def get_value_statistics(values: np.ndarray) -> Statistics:
    """Get statistics for valid values in a numpy array."""
    values = np.ma.masked_invalid(values)
    if values.mask.all():
        return None

    return Statistics(
        min=np.min(values),
        max=np.max(values),
        mean=np.mean(values),
        std=np.std(values),
    )
