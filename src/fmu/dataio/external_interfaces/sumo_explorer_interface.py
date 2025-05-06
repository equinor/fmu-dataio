from io import BytesIO
from uuid import UUID

from pandas import DataFrame

from fmu.sumo.explorer import Explorer
from fmu.sumo.explorer.objects import SearchContext


class SumoExplorerInterface:
    _search_context: SearchContext

    def __init__(
        self, case_id: UUID, ensemble_name: str, standard_result_name: str
    ) -> None:
        self._case_id = case_id
        self._ensemble_name = ensemble_name

        # Using sumo dev for now while this is in POC stage
        # TODO: Use sumo prod when ready
        sumo = Explorer(env="dev")

        case = sumo.get_case_by_uuid(self._case_id)
        self._search_context = case.filter(
            iteration=self._ensemble_name, standard_result=standard_result_name
        )

    def get_realization(self, realization_id: int) -> dict[str, DataFrame]:
        search_context_realization = self._search_context.filter(
            realization=realization_id
        )

        data_frames: dict[str, DataFrame] = {}
        for object in search_context_realization:
            data_frames[object.name] = object.to_pandas()

        return data_frames

    def get_realization_with_metadata(
        self, realization_id: int
    ) -> list[tuple[DataFrame, dict]]:
        search_context_realization = self._search_context.filter(
            realization=realization_id
        )

        realization_data: list[tuple[DataFrame, dict]] = []
        for object in search_context_realization:
            data_frame: DataFrame = object.to_pandas()
            metadata: dict = object.metadata
            realization_data.append((data_frame, metadata))

        return realization_data

    def get_blob(self, realization_id: int) -> dict[str, BytesIO]:
        search_context_realization = self._search_context.filter(
            realization=realization_id
        )

        blobs: dict[str, BytesIO] = {}
        for object in search_context_realization:
            blobs[object.name] = object.blob

        return blobs

    def get_realization_ids(self) -> list[int]:
        return self._search_context.realizationids
