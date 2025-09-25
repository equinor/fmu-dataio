import os
from io import BytesIO

import pandas as pd
import xtgeo
from fmu.datamodels.fmu_results.enums import ObjectMetadataClass
from fmu.sumo.explorer import Explorer
from fmu.sumo.explorer.objects import SearchContext
from pandas import DataFrame


class SumoExplorerInterface:
    def __init__(
        self,
        case_id: str,
        ensemble_name: str,
        fmu_class: ObjectMetadataClass,
        standard_result_name: str,
    ) -> None:
        self._case_id: str = case_id
        self._ensemble_name: str = ensemble_name
        self._fmu_class: ObjectMetadataClass = fmu_class

        env = "prod"
        if "bleeding" in os.environ.get(
            "KOMODO_RELEASE", os.environ.get("KOMODO_RELEASE_BACKUP", "")
        ):
            env = "dev"

        sumo = Explorer(env=env)
        case = sumo.get_case_by_uuid(self._case_id)
        self._search_context: SearchContext = case.filter(
            iteration=self._ensemble_name, standard_result=standard_result_name
        )

    def _get_formatted_data(
        self, data_object: SearchContext
    ) -> DataFrame | xtgeo.Polygons | xtgeo.RegularSurface:
        """Get a fmu-dataio formatted data object from the Sumo Explorer object."""

        match self._fmu_class:
            case ObjectMetadataClass.table:
                return data_object.to_pandas()

            case ObjectMetadataClass.polygons:
                data_frame: DataFrame = pd.read_parquet(
                    data_object.blob, engine="pyarrow"
                )
                return xtgeo.Polygons(data_frame)

            case ObjectMetadataClass.surface:
                # Dataformat: 'irap_binary'
                return data_object.to_regular_surface()

            case _:
                raise ValueError(f"Unknown FMUClass {self._fmu_class}. in provided ")

    def get_objects_with_metadata(
        self, realization_id: int
    ) -> list[tuple[DataFrame | xtgeo.Polygons | xtgeo.RegularSurface, dict]]:
        """
        Get the standard results data objects and metadata from Sumo,
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

    def get_blobs_with_metadata(
        self, realization_id: int
    ) -> list[tuple[BytesIO, dict]]:
        """
        Get the standard results data blobs and metadata from Sumo,
        filtered on the provided realization id. The results are returned
        as a list of tuples containing the blobs and metadata.
        """

        search_context_realization = self._search_context.filter(
            realization=realization_id
        )
        return [(object.blob, object.metadata) for object in search_context_realization]

    def get_realization_ids(self) -> list[int]:
        """Get a list of the standard results realization ids from Sumo."""
        return self._search_context.realizationids
