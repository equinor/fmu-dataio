from io import BytesIO
from uuid import UUID

import pandas as pd
import xtgeo
from pandas import DataFrame

from fmu.dataio._models.fmu_results.enums import FMUClass
from fmu.sumo.explorer import Explorer
from fmu.sumo.explorer.objects import SearchContext


class SumoExplorerInterface:
    def __init__(
        self,
        case_id: UUID,
        ensemble_name: str,
        fmu_class: FMUClass,
        standard_result_name: str,
    ) -> None:
        self._case_id: UUID = case_id
        self._ensemble_name: str = ensemble_name
        self._fmu_class: FMUClass = fmu_class

        # TODO: Use sumo prod when ready
        sumo = Explorer(env="dev")
        case = sumo.get_case_by_uuid(self._case_id)
        self._search_context: SearchContext = case.filter(
            iteration=self._ensemble_name, standard_result=standard_result_name
        )

    def _get_formatted_data(
        self, data_object: SearchContext
    ) -> DataFrame | xtgeo.Polygons | xtgeo.RegularSurface:
        """Get a fmu-dataio formatted data object from the Sumo Explorer object."""

        match self._fmu_class:
            case FMUClass.table:
                return data_object.to_pandas()

            case FMUClass.polygons:
                data_frame: DataFrame = pd.read_parquet(
                    data_object.blob, engine="pyarrow"
                )
                return xtgeo.Polygons(data_frame)

            case FMUClass.surface:
                # Dataformat: 'irap_binary'
                return data_object.to_regular_surface()

            case _:
                raise ValueError(f"Unknown FMUClass {self._fmu_class}. in provided ")

    def get_realization(
        self, realization_id: int
    ) -> dict[str, DataFrame | xtgeo.Polygons | xtgeo.RegularSurface]:
        """
        Get the standard results data objects from Sumo,
        filtered on the provided realization id.
        The results are returned as key value pairs, with the
        data name as key and a fmu-dataio formatted data object as value.
        """

        search_context_realization = self._search_context.filter(
            realization=realization_id
        )

        realization_data: dict[
            str, DataFrame | xtgeo.Polygons | xtgeo.RegularSurface
        ] = {}
        for object in search_context_realization:
            realization_data[object.name] = self._get_formatted_data(object)
        return realization_data

    def get_realization_with_metadata(
        self, realization_id: int
    ) -> list[tuple[DataFrame | xtgeo.Polygons | xtgeo.RegularSurface, dict]]:
        """
        Get the standard results data and metadata from Sumo,
        filtered on the provided realization id. The results are returned
        as a list of tuples containing the data and metadata.
        """

        search_context_realization = self._search_context.filter(
            realization=realization_id
        )

        realization_data: list[
            tuple[DataFrame | xtgeo.Polygons | xtgeo.RegularSurface, dict]
        ] = []
        for object in search_context_realization:
            realization_data.append((self._get_formatted_data(object), object.metadata))

        return realization_data

    def get_blobs(self, realization_id: int) -> dict[str, BytesIO]:
        """
        Get the standard results data blobs from Sumo,
        filtered on the provided realization id.
        The results are returned as key value pairs,
        with the data name as key and the data blob as value.
        """
        search_context_realization = self._search_context.filter(
            realization=realization_id
        )

        blobs: dict[str, BytesIO] = {}
        for object in search_context_realization:
            blobs[object.name] = object.blob

        return blobs

    def get_realization_ids(self) -> list[int]:
        """Get a list of the standard results realization ids from Sumo."""
        return self._search_context.realizationids
