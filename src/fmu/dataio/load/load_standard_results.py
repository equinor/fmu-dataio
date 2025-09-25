from io import BytesIO
from pathlib import Path
from typing import TypeAlias

import numpy as np
import xtgeo
from pandas import DataFrame

from fmu.dataio.export._decorators import experimental
from fmu.dataio.external_interfaces.schema_validation_interface import (
    SchemaValidationInterface,
)
from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface
from fmu.datamodels.fmu_results.enums import ObjectMetadataClass
from fmu.datamodels.standard_results.enums import StandardResultName

DataFrameOrXtgeoObject: TypeAlias = DataFrame | xtgeo.Polygons | xtgeo.RegularSurface


class StandardResultsLoader:
    """The generic class for loaded standard results in fmu-dataio."""

    def __init__(
        self,
        case_id: str,
        ensemble_name: str,
        fmu_class: ObjectMetadataClass,
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
        realization id. The `key` is a string based on the object name.

        Args:
            realization_id: The id of the realization to filter on.

        """

        data_dict: dict[str, DataFrameOrXtgeoObject] = {}
        for object, metadata in self._sumo_interface.get_objects_with_metadata(
            realization_id
        ):
            object_key = self._construct_object_key(metadata)
            data_dict[object_key] = object

        return data_dict

    def get_blobs(self, realization_id: int) -> dict[str, BytesIO]:
        """
        Returns a dictionary with the loaded objects blobs, filtered on the
        provided realization id. The `key` is a string based on the object name.

        Args:
            realization_id: The id of the realization to filter on.

        """

        blobs_dict: dict[str, BytesIO] = {}
        for blob, metadata in self._sumo_interface.get_blobs_with_metadata(
            realization_id
        ):
            object_key = self._construct_object_key(metadata)
            blobs_dict[object_key] = blob

        return blobs_dict

    @staticmethod
    def _generate_path_for_saving(
        folder_path: str, metadata: dict, file_extention: str
    ) -> Path:
        """
        Generate the path to save the object to,
        based on the provided path and metadata.
        """

        case_name = metadata["fmu"]["case"]["name"]
        relative_path = Path(metadata["file"]["relative_path"])
        relative_folder_path = relative_path.parent
        file_path = Path(folder_path) / Path(case_name) / relative_folder_path
        file_path.mkdir(parents=True, exist_ok=True)

        file_name = relative_path.name.replace(relative_path.suffix, file_extention)

        return file_path / Path(file_name)

    @staticmethod
    def _construct_object_key(object_metadata: dict) -> str:
        """Construct a unique key from the provided object metadata"""

        data_name: str = object_metadata["data"]["name"]
        object_name = data_name.lower().replace(" ", "_").replace(".", "")
        standard_result_name = object_metadata["data"]["standard_result"]["name"]

        if standard_result_name == StandardResultName.fluid_contact_surface:
            fluid_contact_type = object_metadata["data"]["fluid_contact"]["contact"]
            return f"{object_name}-{fluid_contact_type}"

        return object_name

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
        self, case_id: str, ensemble_name: str, standard_result_name: str
    ) -> None:
        super().__init__(
            case_id,
            ensemble_name,
            ObjectMetadataClass.table,
            standard_result_name,
        )

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

        data_frames_with_metadata: list[tuple[DataFrame, dict]] = (
            self._sumo_interface.get_objects_with_metadata(realization_id)
        )

        file_paths: list[str] = []
        for data_frame, metadata in data_frames_with_metadata:
            self._validate_object(
                data_frame=data_frame,
                schema_url=metadata["data"]["standard_result"]["file_schema"]["url"],
            )

            file_path = self._generate_path_for_saving(folder_path, metadata, ".csv")
            data_frame.to_csv(file_path, index=False)
            file_paths.append(str(file_path))

        return file_paths


class PolygonStandardResultsLoader(StandardResultsLoader):
    """Base class for the loaded polygon standard results in fmu-dataio"""

    def __init__(
        self, case_id: str, ensemble_name: str, standard_result_name: str
    ) -> None:
        super().__init__(
            case_id, ensemble_name, ObjectMetadataClass.polygons, standard_result_name
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

        plygons_with_metadata: list[tuple[xtgeo.Polygons, dict]] = (
            self._sumo_interface.get_objects_with_metadata(realization_id)
        )

        file_paths: list[str] = []
        for polygon, metadata in plygons_with_metadata:
            # Temporary work-around until xtgeo.Polygons supports storing
            # csv files directly with Polygons.to_file()
            # https://github.com/equinor/xtgeo/issues/1333
            data_frame = polygon.get_dataframe()

            self._validate_object(
                data_frame=data_frame,
                schema_url=metadata["data"]["standard_result"]["file_schema"]["url"],
            )

            file_path = self._generate_path_for_saving(folder_path, metadata, ".csv")
            data_frame.to_csv(file_path, index=False)
            file_paths.append(str(file_path))

        return file_paths


class SurfacesStandardResultsLoader(StandardResultsLoader):
    """Base class for the loaded surface standard results in fmu-dataio"""

    def __init__(
        self, case_id: str, ensemble_name: str, standard_result_name: str
    ) -> None:
        super().__init__(
            case_id,
            ensemble_name,
            ObjectMetadataClass.surface,
            standard_result_name,
        )

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

        surfaces_with_metadata: list[tuple[xtgeo.RegularSurface, dict]] = (
            self._sumo_interface.get_objects_with_metadata(realization_id)
        )

        file_paths: list[str] = []
        for surface, metadata in surfaces_with_metadata:
            file_path = self._generate_path_for_saving(folder_path, metadata, ".gri")
            surface.to_file(file_path, fformat="irap_binary")
            file_paths.append(str(file_path))

        return file_paths


class InplaceVolumesLoader(TabularStandardResultsLoader):
    """
    Loader object for the Inplace Volumes standard results in fmu-dataio.
    Offers a set of methods to easily manage and interact
    with the loaded inplace volumes data.
    """

    def __init__(self, case_id: str, ensemble_name: str):
        super().__init__(case_id, ensemble_name, StandardResultName.inplace_volumes)


class FieldOutlinesLoader(PolygonStandardResultsLoader):
    """
    Loader object for the Field Outline standard results in fmu-dataio.
    Offers a set of methods to easily manage and interact
    with the loaded field outlines data.
    """

    def __init__(self, case_id: str, ensemble_name: str) -> None:
        super().__init__(case_id, ensemble_name, StandardResultName.field_outline)


class StructureDepthSurfacesLoader(SurfacesStandardResultsLoader):
    """
    Loader object for the Structure Depth Surface standard results in fmu-dataio.
    Offers a set of methods to easily manage and interact
    with the loaded structure depth surfaces data.
    """

    def __init__(self, case_id: str, ensemble_name: str) -> None:
        super().__init__(
            case_id, ensemble_name, StandardResultName.structure_depth_surface
        )


class FluidContactSurfacesLoader(SurfacesStandardResultsLoader):
    """
    Loader object for the Fluid Contact Surfaces standard results in fmu-dataio.
    Offers a set of methods to easily manage and interact
    with the loaded fluid contact surfaces data.
    """

    def __init__(self, case_id: str, ensemble_name: str) -> None:
        super().__init__(
            case_id, ensemble_name, StandardResultName.fluid_contact_surface
        )


@experimental
def load_inplace_volumes(case_id: str, ensemble_name: str) -> InplaceVolumesLoader:
    """
    This function provides a simplified interface for loading inplace volumes
    standard results from Sumo. It returns an InplaceVolumesLoader object, which offers
    a set of methods to easily manage and interact with the loaded inplace volumes data.

    Args:
        case_id: The id of the case to load inplace volumes from.
        ensemble_name: The name of the ensemble to load inplace volumes from.

    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in a script::

            from fmu.dataio.load.load_standard_results import load_inplace_volumes

            inplace_volumes_loader = load_inplace_volumes(case_id, ensemble_name)

            # Get all inplace volumes objects for a given realization
            objects = inplace_volumes_loader.get_realization(realization_id)

            # Save the inplace volumes objects for a given realization
            object_paths = inplace_volumes_loader.save_realization(realization_id, folder_path)

    """  # noqa: E501 line too long

    return InplaceVolumesLoader(case_id, ensemble_name)


@experimental
def load_field_outlines(case_id: str, ensemble_name: str) -> FieldOutlinesLoader:
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
        Example usage in a script::

            from fmu.dataio.load.load_standard_results import load_field_outlines

            field_outlines_loader = load_field_outlines(case_id, ensemble_name)

            # Get all field outlines objects for a given realization
            objects = field_outlines_loader.get_realization(realization_id)

            # Save the field outlines objects for a given realization
            object_paths = field_outlines_loader.save_realization(realization_id, folder_path)

    """  # noqa: E501 line too long

    return FieldOutlinesLoader(case_id, ensemble_name)


@experimental
def load_structure_depth_surfaces(
    case_id: str, ensemble_name: str
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
        Example usage in a script::

            from fmu.dataio.load.load_standard_results import load_structure_depth_surfaces

            structure_depth_surfaces_loader = load_structure_depth_surfaces(case_id, ensemble_name)

            # Get all structure depth surfaces objects for a given realization
            objects = structure_depth_surfaces_loader.get_realization(realization_id)

            # Save the structure depth surfaces objects for a given realization
            object_paths = structure_depth_surfaces_loader.save_realization(realization_id, folder_path)

    """  # noqa: E501 line too long

    return StructureDepthSurfacesLoader(case_id, ensemble_name)


@experimental
def load_fluid_contact_surfaces(
    case_id: str, ensemble_name: str
) -> FluidContactSurfacesLoader:
    """
    This function provides a simplified interface for loading fluid contact surfaces
    standard results from Sumo. It returns a FluidContactSurfacesLoader object,
    which offers a set of methods to easily manage and interact with the
    loaded fluid contact surfaces data.

    Args:
        case_id: The id of the case to load fluid contact surfaces from.
        ensemble_name: The name of the ensemble to load fluid contact surfaces from.

    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in a script::

            from fmu.dataio.load.load_standard_results import load_fluid_contact_surfaces

            fluid_contact_surfaces_loader = load_fluid_contact_surfaces(case_id, ensemble_name)

            # Get all fluid contact surface objects for a given realization
            objects = fluid_contact_surfaces_loader.get_realization(realization_id)

            # Save the fluid contact surface objects for a given realization
            object_paths = fluid_contact_surfaces_loader.save_realization(realization_id, folder_path)

    """  # noqa: E501 line too long

    return FluidContactSurfacesLoader(case_id, ensemble_name)
