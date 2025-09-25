import os
from io import BytesIO
from uuid import UUID

import pandas as pd
import xtgeo
from fmu.datamodels.fmu_results.enums import Layout, ObjectMetadataClass
from fmu.sumo.explorer import Explorer
from fmu.sumo.explorer.objects import SearchContext
from pandas import DataFrame

from fmu.dataio._readers.tsurf import TSurfData


class SumoExplorerInterface:
    def __init__(
        self,
        case_id: UUID,
        ensemble_name: str,
        fmu_class: ObjectMetadataClass,
        fmu_layout: Layout,
        standard_result_name: str,
    ) -> None:
        self._case_id: UUID = case_id
        self._ensemble_name: str = ensemble_name
        self._fmu_class: ObjectMetadataClass = fmu_class
        self._fmu_layout: Layout = fmu_layout

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

    # NOTE: 'SeachContext' could possibly be replaced by 'Child'
    def _get_formatted_data(
        self, data_object: SearchContext
    ) -> DataFrame | xtgeo.Polygons | xtgeo.RegularSurface | TSurfData:
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
                match self._fmu_layout:
                    case Layout.regular:
                        # TODO: @ecs: "data_object.to_regular_surface()": is defined
                        # somewhere in SUMO; Child, Document, Realization...?
                        return data_object.to_regular_surface()

                    case Layout.triangulated:
                        # TODO: proposed by Copilot, is most likely wrong
                        # Probably we need new functionality in SUMO
                        return TSurfData.from_blob(data_object.blob)

                    case _:
                        raise ValueError(
                            f"Unknown FMULayout {self._fmu_layout} in provided"
                        )

            case _:
                raise ValueError(f"Unknown FMUClass {self._fmu_class}. in provided ")

    def get_objects_with_metadata(
        self, realization_id: int
    ) -> list[
        tuple[DataFrame | xtgeo.Polygons | xtgeo.RegularSurface | TSurfData, dict]
    ]:
        """
        Get the standard results data objects and metadata from Sumo,
        filtered on the provided realization id. The results are returned
        as a list of tuples containing the data and metadata.
        """

        search_context_realization = self._search_context.filter(
            realization=realization_id
        )

        realization_data: list[
            tuple[DataFrame | xtgeo.Polygons | xtgeo.RegularSurface | TSurfData, dict]
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
