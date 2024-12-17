from __future__ import annotations

from enum import Enum
from typing import Final


class InplaceVolumes:
    """Enumerations relevant to inplace volumes tables."""

    class Fluid(str, Enum):
        """Fluid types"""

        OIL = "OIL"
        GAS = "GAS"
        WATER = "WATER"

    class TableIndexColumns(str, Enum):
        """The index columns for an inplace volumes table."""

        FLUID = "FLUID"
        ZONE = "ZONE"
        REGION = "REGION"
        FACIES = "FACIES"
        LICENSE = "LICENSE"

    FLUID_COLUMN: Final = TableIndexColumns.FLUID
    """The column name and value used to indicate the index value for fluid type."""

    class VolumetricColumns(str, Enum):
        """The value columns for an inplace volumes table."""

        BULK = "BULK"
        NET = "NET"
        PORV = "PORV"
        HCPV = "HCPV"
        STOIIP = "STOIIP"
        GIIP = "GIIP"
        ASSOCIATEDGAS = "ASSOCIATEDGAS"
        ASSOCIATEDOIL = "ASSOCIATEDOIL"

    @staticmethod
    def index_columns() -> list[str]:
        """Returns a list of the index columns."""
        return [k.value for k in InplaceVolumes.TableIndexColumns]

    @staticmethod
    def value_columns() -> list[str]:
        """Returns a list of the value columns."""
        return [k.value for k in InplaceVolumes.VolumetricColumns]

    @staticmethod
    def table_columns() -> list[str]:
        """Returns a list of all table columns."""
        return InplaceVolumes.index_columns() + InplaceVolumes.value_columns()
