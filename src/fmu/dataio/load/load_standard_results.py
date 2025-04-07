from typing import Generic, TypeVar
from uuid import UUID

import numpy as np

from fmu.dataio.export._decorators import experimental
from fmu.dataio.external_interfaces.schema_validation_interface import (
    SchemaValidationInterface,
)
from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface
from fmu.sumo.explorer.objects import SearchContext, Table

T = TypeVar("T")


class LoadedStandardResults(Generic[T]):
    """The generic class for loaded standard results in fmu-dataio."""

    def list_realizations(self) -> list[int]:
        return self._filter_result.realizationids  # type:ignore

    def concatenate_realizations(self) -> T:
        raise NotImplementedError

    def get_realization(self, realization_id: int) -> T:
        # What should we return here?
        return self._filter_result.tables.filter(realization_id)  # type:ignore

    def validate_metadata(self) -> None:
        """Validate the standard results metadata against its schema"""

        validator_interface = SchemaValidationInterface()
        for metadata in self.metadata:  # type:ignore
            # Should we return a report or fail all?
            # Failing all for now
            validator_interface.validate_against_schema(
                schema_url=metadata["$schema"], data=metadata
            )

    def validate_objects(self) -> None:
        """Validate the standard results objects against its schema"""

        validator_interface = SchemaValidationInterface()
        for object in self.standard_results:  # type:ignore
            # Should we return a report or fail all?
            # Failing all for now
            data_frame = (
                object.to_pandas().replace(np.nan, None).to_dict(orient="records")
            )
            validator_interface.validate_against_schema(
                schema_url=object.metadata["data"]["product"]["file_schema"]["url"],
                data=data_frame,
            )


class InplaceVolumes(LoadedStandardResults[T]):
    """Class representing a set of Inplace Volumes in fmu-dataio."""

    _inplace_volumes: list[Table] = []
    _inplace_volumes_metadata: list[dict] = []

    def __init__(self, filter_result: SearchContext) -> None:
        self._filter_result: SearchContext = filter_result
        self._set_inplace_volumes()
        self._set_metadata()

    @property
    def metadata(self) -> list[dict]:
        """Return inplace volumes metadata

        Returns:
            list[dict]: the metadata for each inplace volume object
        """
        return self._inplace_volumes_metadata

    @property
    def standard_results(self) -> list[Table]:
        """Return the inplace volumes

        Returns:
            list[Table]: the metadata for each inplace volume object
        """
        return self._inplace_volumes

    def _set_inplace_volumes(self) -> None:
        for table in self._filter_result:
            # While we wait for Sumo to add a filter for standard results
            if "product" in table.metadata["data"]:
                self._inplace_volumes.append(table)

    def _set_metadata(self) -> None:
        self._inplace_volumes_metadata = [
            table.metadata for table in self._inplace_volumes
        ]


class StructureDepthSurfaces(LoadedStandardResults[T]):
    def __init__(self) -> None:
        raise NotImplementedError


@experimental
def load_inplace_volumes(case_id: UUID, ensemble_name: str) -> InplaceVolumes:
    """Simplified interface to load inplace volumes standard results from Sumo."""

    filter_result = SumoExplorerInterface(
        case_id=case_id, ensemble_name=ensemble_name
    ).get_volume_tables()

    return InplaceVolumes(filter_result)


@experimental
def load_structure_depth_surfaces(
    case_id: UUID, ensemble_name: str
) -> StructureDepthSurfaces:
    """Simplified interface to load structure depth surfaces
    standard results from Sumo."""

    raise NotImplementedError
