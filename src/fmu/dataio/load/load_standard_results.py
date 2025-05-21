from io import BytesIO
from pathlib import Path
from typing import TypeAlias
from uuid import UUID

import numpy as np
import xtgeo
from pandas import DataFrame

from fmu.dataio._models.fmu_results.enums import FMUClass, StandardResultName
from fmu.dataio.export._decorators import experimental
from fmu.dataio.external_interfaces.schema_validation_interface import (
    SchemaValidationInterface,
)
from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface

DataFrameOrXtgeoObject: TypeAlias = DataFrame | xtgeo.Polygons | xtgeo.RegularSurface


class StandardResultsLoader:
    """The generic class for loaded standard results in fmu-dataio."""

    def __init__(
        self,
        case_id: UUID,
        ensemble_name: str,
        fmu_class: FMUClass,
        standard_result_name: str,
    ) -> None:
        self._sumo_interface = SumoExplorerInterface(
            case_id, ensemble_name, fmu_class, standard_result_name
        )

    def list_realizations(self) -> list[int]:
        """Returns a list with the realization ids of the loaded objects."""

        return self._sumo_interface.get_realization_ids()

    def get_realization(self, realization_id: int) -> dict[str, DataFrameOrXtgeoObject]:
        """
        Returns a dictionary with the loaded objects, filtered on the provided
        realization id. The `key` is the object name.

        Args:
            realization_id: The id of the realization to filter on.

        """

        return self._sumo_interface.get_realization(realization_id)

    def get_blobs(self, realization_id: int) -> dict[str, BytesIO]:
        """
        Returns a dictionary with the loaded objects blobs, filtered on the
        provided realization id. The `key` is the object name.

        Args:
            realization_id: The id of the realization to filter on.

        """

        return self._sumo_interface.get_blobs(realization_id)

    @staticmethod
    def _generate_path_for_saving(
        folder_path: str, metadata: dict, file_extention: str
    ) -> Path:
        """
        Generate the path to save the object to,
        based on the provided path and metadata.
        """

        file_path = Path(
            f"{folder_path}/"
            f"{metadata['fmu']['case']['name']}/"
            f"{metadata['fmu']['realization']['name']}/"
            f"{metadata['fmu']['ensemble']['name']}/"
        )

        file_name = (
            (
                f"{metadata['data']['standard_result']['name']}-"
                f"{metadata['data']['name']}"
                f".{file_extention}"
            )
            .lower()
            .replace(" ", "")
        )
        file_path.mkdir(parents=True, exist_ok=True)
        return file_path / Path(file_name)

    @staticmethod
    def _validate_object(data_frame: DataFrame, schema_url: str) -> None:
        """Validate the standard result object against its schema"""

        validator_interface = SchemaValidationInterface()
        validator_interface.validate_against_schema(
            schema_url=schema_url,
            data=data_frame.replace(np.nan, None).to_dict(orient="records"),
        )


class TabularStandardResultsLoader(StandardResultsLoader):
    """Base class for the loaded tabular standard results in fmu-dataio"""

    def __init__(
        self, case_id: UUID, ensemble_name: str, standard_result_name: str
    ) -> None:
        super().__init__(case_id, ensemble_name, FMUClass.table, standard_result_name)

    def get_realization(self, realization_id: int) -> dict[str, DataFrame]:
        return super().get_realization(realization_id)

    def save_realization(self, realization_id: int, folder_path: str) -> list[str]:
        """
        Saves the loaded tabular objects, filtered on the provided
        realization id, as csv files at the provided path.

        Args:
            realization_id: The id of the realization to filter on.
            folder_path: The path to where to store the generated csv files.

        """

        realization_data: list[tuple[DataFrame, dict]] = (
            self._sumo_interface.get_realization_with_metadata(realization_id)
        )

        file_paths: list[str] = []
        for data_frame, metadata in realization_data:
            self._validate_object(
                data_frame=data_frame,
                schema_url=metadata["data"]["standard_result"]["file_schema"]["url"],
            )

            file_path = self._generate_path_for_saving(folder_path, metadata, "csv")
            data_frame.to_csv(file_path, index=False)
            file_paths.append(str(file_path))

        return file_paths


class PolygonStandardResultsLoader(StandardResultsLoader):
    """Base class for the loaded polygon standard results in fmu-dataio"""

    def __init__(
        self, case_id: UUID, ensemble_name: str, standard_result_name: str
    ) -> None:
        super().__init__(
            case_id, ensemble_name, FMUClass.polygons, standard_result_name
        )

    def get_realization(self, realization_id: int) -> dict[str, xtgeo.Polygons]:
        return super().get_realization(realization_id)

    def save_realization(self, realization_id: int, folder_path: str) -> list[str]:
        """
        Saves the loaded polygon objects, filtered on the provided
        realization id, as csv files at the provided path.

        Args:
            realization_id: The id of the realization to filter on.
            folder_path: The path to where to store the generated csv files.

        """

        realization_data: list[tuple[xtgeo.Polygons, dict]] = (
            self._sumo_interface.get_realization_with_metadata(realization_id)
        )

        file_paths: list[str] = []
        for polygon, metadata in realization_data:
            # Temporary work-around until xtgeo.Polygons supports storing
            # csv files directly with Polygons.to_file()
            # https://github.com/equinor/xtgeo/issues/1333
            data_frame = polygon.get_dataframe()

            self._validate_object(
                data_frame=data_frame,
                schema_url=metadata["data"]["standard_result"]["file_schema"]["url"],
            )

            file_path = self._generate_path_for_saving(folder_path, metadata, "csv")
            data_frame.to_csv(file_path, index=False)
            file_paths.append(str(file_path))

        return file_paths


class SurfacesStandardResultsLoader(StandardResultsLoader):
    """Base class for the loaded surface standard results in fmu-dataio"""

    def __init__(
        self, case_id: UUID, ensemble_name: str, standard_result_name: str
    ) -> None:
        super().__init__(case_id, ensemble_name, FMUClass.surface, standard_result_name)

    def get_realization(self, realization_id: int) -> dict[str, xtgeo.RegularSurface]:
        return super().get_realization(realization_id)

    def save_realization(self, realization_id: int, folder_path: str) -> list[str]:
        """
        Saves the loaded surface objects, filtered on the provided
        realization id, as irap binary files at the provided path.

        Args:
            realization_id: The id of the realization to filter on.
            folder_path: The path to where to store the generated irap binary files.

        """

        realization_data: list[tuple[xtgeo.RegularSurface, dict]] = (
            self._sumo_interface.get_realization_with_metadata(realization_id)
        )

        file_paths: list[str] = []
        for surface, metadata in realization_data:
            file_path = self._generate_path_for_saving(folder_path, metadata, "gri")
            surface.to_file(file_path, fformat="irap_binary")
            file_paths.append(str(file_path))

        return file_paths


class InplaceVolumesLoader(TabularStandardResultsLoader):
    """
    Loader object for the Inplace Volumes standard results in fmu-dataio.
    Offers a set of methods to easily manage and interact
    with the loaded inplace volumes data.
    """

    def __init__(self, case_id: UUID, ensemble_name: str):
        super().__init__(case_id, ensemble_name, StandardResultName.inplace_volumes)


class FieldOutlinesLoader(PolygonStandardResultsLoader):
    """
    Loader object for the Field Outline standard results in fmu-dataio.
    Offers a set of methods to easily manage and interact
    with the loaded field outlines data.
    """

    def __init__(self, case_id: UUID, ensemble_name: str) -> None:
        super().__init__(case_id, ensemble_name, StandardResultName.field_outline)


class StructureDepthSurfacesLoader(SurfacesStandardResultsLoader):
    """
    Loader object for the Structure Depth Surface standard results in fmu-dataio.
    Offers a set of methods to easily manage and interact
    with the loaded structure depth surfaces data.
    """

    def __init__(self, case_id: UUID, ensemble_name: str) -> None:
        super().__init__(
            case_id, ensemble_name, StandardResultName.structure_depth_surface
        )


@experimental
def load_inplace_volumes(case_id: UUID, ensemble_name: str) -> InplaceVolumesLoader:
    """
    This function provides a simplified interface for loading inplace volumes
    standard results from Sumo. It returns an InplaceVolumeLoader object, which offers
    a set of methods to easily manage and interact with the loaded inplace volumes data.

    Args:
        case_id: The id of the case to load inplace volumes from.
        ensemble_name: The name of the ensemble to load inplace volumes from.

    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in a script:

            from fmu.dataio.load.load_standard_results import load_inplace_volumes

            inplace_volumes_loader = load_inplace_volumes(case_id, ensemble_name)

            realization_data = inplace_volumes_loader.get_realization(realization_id)

    """  # noqa: E501 line too long

    return InplaceVolumesLoader(case_id, ensemble_name)


@experimental
def load_field_outlines(case_id: UUID, ensemble_name: str) -> FieldOutlinesLoader:
    """
    This function provides a simplified interface for loading field outlines
    standard results from Sumo. It returns a FieldOutlinesLoader object, which offers
    a set of methods to easily manage and interact with the loaded field outlines data.

    Args:
        case_id: The id of the case to load field outlines from.
        ensemble_name: The name of the ensemble to load field outlines from.

    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in a script:

            from fmu.dataio.load.load_standard_results import load_field_outlines

            field_outlines_loader = load_field_outlines(case_id, ensemble_name)

            realization_data = field_outlines_loader.get_realization(realization_id)

    """  # noqa: E501 line too long

    return FieldOutlinesLoader(case_id, ensemble_name)


@experimental
def load_structure_depth_surfaces(
    case_id: UUID, ensemble_name: str
) -> StructureDepthSurfacesLoader:
    """
    This function provides a simplified interface for loading structure depth surfaces
    standard results from Sumo. It returns a StructureDepthSurfacesLoader object,
    which offers a set of methods to easily manage and interact with the
    loaded structure depth surfaces data.

    Args:
        case_id: The id of the case to load structure depth surfaces from.
        ensemble_name: The name of the ensemble to load structure depth surfaces from.

    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in a script:

            from fmu.dataio.load.load_standard_results import load_structure_depth_surfaces

            structure_depth_surfaces_loader = load_structure_depth_surfaces(case_id, ensemble_name)

            realization_data = structure_depth_surfaces_loader.get_realization(realization_id)

    """  # noqa: E501 line too long

    return StructureDepthSurfacesLoader(case_id, ensemble_name)
