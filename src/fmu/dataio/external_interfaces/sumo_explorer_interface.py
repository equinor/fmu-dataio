from uuid import UUID

from fmu.sumo.explorer import Explorer
from fmu.sumo.explorer.objects import Surface, Table


class SumoExplorerInterface:
    def __init__(self, case_id: UUID) -> None:
        sumo = Explorer()
        self._case = sumo.get_case_by_uuid(case_id)

    def get_inplace_volumes_standard_results(self) -> list[Table]:
        # Later we can probably filter on "standard_result" here
        tables = self._case.tables.filter(content="volumes", dataformat="parquet")

        inplace_volumes_standard_results: list[Table] = []
        for table in tables:
            # While we wait for Sumo to add a filter for standard results
            if "product" in table.metadata["data"]:
                inplace_volumes_standard_results.append(table)

        return inplace_volumes_standard_results

    def get_structure_depth_surfaces_standard_results(self) -> list[Surface]:
        # Later we can probably filter on "standard_result" here
        surfaces = self._case.surfaces.filter(
            content="depth",
        )

        structure_depth_surfaces_standard_results: list[Surface] = []
        for surface in surfaces:
            # While we wait for Sumo to add a filter for standard results
            if "product" in surface.metadata["data"]:
                structure_depth_surfaces_standard_results.append(surface)

        return structure_depth_surfaces_standard_results
