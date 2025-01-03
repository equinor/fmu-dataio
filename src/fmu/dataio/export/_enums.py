from __future__ import annotations

from enum import Enum


class InplaceVolumes:
    """Enumerations relevant to inplace volumes tables."""

    class Fluid(str, Enum):
        """Fluid types used as values in the FLUID column."""

        oil = "oil"
        gas = "gas"
        water = "water"

    class TableIndexColumns(str, Enum):
        """The index columns for an inplace volumes table."""

        FLUID = "FLUID"
        ZONE = "ZONE"
        REGION = "REGION"
        FACIES = "FACIES"
        LICENSE = "LICENSE"

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
    def required_index_columns() -> list[str]:
        return [
            InplaceVolumes.TableIndexColumns.FLUID.value,
            InplaceVolumes.TableIndexColumns.ZONE.value,
            InplaceVolumes.TableIndexColumns.REGION.value,
        ]

    @staticmethod
    def value_columns() -> list[str]:
        """Returns a list of the value columns."""
        return [k.value for k in InplaceVolumes.VolumetricColumns]

    @staticmethod
    def required_value_columns() -> list[str]:
        """Returns a list of the value columns."""
        return [
            InplaceVolumes.VolumetricColumns.BULK.value,
            InplaceVolumes.VolumetricColumns.NET.value,
            InplaceVolumes.VolumetricColumns.PORV.value,
            InplaceVolumes.VolumetricColumns.HCPV.value,
        ]

    @staticmethod
    def required_columns() -> list[str]:
        """Returns a list of the columns required at export."""
        return (
            InplaceVolumes.required_index_columns()
            + InplaceVolumes.required_value_columns()
        )

    @staticmethod
    def table_columns() -> list[str]:
        """Returns a list of all table columns."""
        return InplaceVolumes.index_columns() + InplaceVolumes.value_columns()
