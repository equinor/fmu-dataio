from dataclasses import dataclass
from uuid import UUID

from fmu.sumo.explorer import Explorer


@dataclass
class SumoExplorerInterface:
    case_id: UUID

    def __post_init__(self) -> None:
        sumo = Explorer()
        self._case = sumo.get_case_by_uuid(self.case_id)

    def get_inplace_volumes_standard_results(self) -> list[dict]:
        # Later we can probably filter on "standard_result" here
        tables = self._case.tables.filter(content="volumes", dataformat="parquet")

        inplace_volumes_standard_results = []
        for table in tables:
            metadata = table.metadata

            # While we wait for Sumo to add a filter for standard results
            if "product" in metadata["data"]:
                inplace_volumes_standard_results.append(metadata)

        return inplace_volumes_standard_results

    def get_structure_depth_surfaces_standard_results(self) -> list[dict]:
        # Later we can probably filter on "standard_result" here
        surfaces = self._case.surfaces.filter(
            content="depth",
        )

        structure_depth_surfaces_standard_results = []
        for surface in surfaces:
            metadata = surface.metadata

            # While we wait for Sumo to add a filter for standard results
            if "product" in metadata["data"]:
                structure_depth_surfaces_standard_results.append(metadata)

        return structure_depth_surfaces_standard_results
