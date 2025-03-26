from dataclasses import dataclass
from uuid import UUID

from fmu.sumo.explorer import Explorer


@dataclass
class SumoExplorerInterface:
    case_id: UUID

    def __post_init__(self) -> None:
        sumo = Explorer()
        self._case = sumo.get_case_by_uuid(self.case_id)

    def get_volume_table_metadata(self) -> list[dict]:
        # Later we can probably filter on "standard_result" here
        tables = self._case.tables.filter(content="volumes", dataformat="parquet")

        volume_table_metadata = []
        for table in tables:
            metadata = table.metadata

            # While we wait for Sumo to add a filter for standard results
            if "product" in metadata["data"]:
                volume_table_metadata.append(metadata)

        return volume_table_metadata

    def get_surface_depth_metadata(self) -> list[dict]:
        # Later we can probably filter on "standard_result" here
        surfaces = self._case.surfaces.filter(
            content="depth",
        )

        surface_depth_metadata = []
        for surface in surfaces:
            metadata = surface.metadata

            # While we wait for Sumo to add a filter for standard results
            if "product" in metadata["data"]:
                surface_depth_metadata.append(metadata)

        return surface_depth_metadata
