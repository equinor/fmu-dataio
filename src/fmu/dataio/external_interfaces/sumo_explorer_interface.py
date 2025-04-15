from uuid import UUID

from fmu.sumo.explorer import Explorer
from fmu.sumo.explorer.objects import Surface, Table


class SumoExplorerInterface:
    def __init__(self, case_id: UUID, ensemble_name: str) -> None:
        self._case_id = case_id
        self._ensemble_name = ensemble_name

    def get_volume_tables(self) -> list[Table]:
        # Later we can probably filter on "standard_result" here
        sumo = Explorer()
        case = sumo.get_case_by_uuid(self._case_id)

        return case.tables.filter(
            content="volumes", dataformat="parquet", iteration=self._ensemble_name
        )

    def get_structure_depth_surfaces_standard_results(self) -> list[Surface]:
        # Later we can probably filter on "standard_result" here
        sumo = Explorer()
        case = sumo.get_case_by_uuid(self._case_id)

        # Later we can probably filter on "standard_result" here
        return case.surfaces.filter(
            content="depth", dataformat="parquet", iteration=self._ensemble_name
        )
