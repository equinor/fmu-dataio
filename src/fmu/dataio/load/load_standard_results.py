from io import BytesIO
from pathlib import Path
from typing import Generic, TypeVar
from uuid import UUID

from pandas import DataFrame

from fmu.dataio._models.fmu_results import enums
from fmu.dataio.export._decorators import experimental
from fmu.dataio.external_interfaces.schema_validation_interface import (
    SchemaValidationInterface,
)
from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface

T = TypeVar("T")


class StandardResultsLoader(Generic[T]):
    """The generic class for loaded standard results in fmu-dataio."""

    def __init__(
        self, case_id: UUID, ensemble_name: str, standard_result_name: str
    ) -> None:
        self._sumo_interface = SumoExplorerInterface(
            case_id, ensemble_name, standard_result_name
        )

    def list_realizations(self) -> list[int]:
        return self._sumo_interface.get_realization_ids()

    def concatenate_realizations(self) -> T:
        raise NotImplementedError

    def save_realization(self, realization_id: int, folder_path: str) -> list[str]:
        realization_data: list[tuple[DataFrame, dict]] = (
            self._sumo_interface.get_realization_with_metadata(realization_id)
        )

        file_paths: list[str] = []
        for data in realization_data:
            data_frame: DataFrame = data[0]
            metadata: dict = data[1]

            self._validate_object(
                data_frame=data[0],
                schema_url=metadata["data"]["standard_result"]["file_schema"]["url"],
            )

            data_name: str = metadata["data"]["name"]
            standard_result_name: str = metadata["data"]["standard_result"]["name"]
            file_name = f"{standard_result_name}_{data_name.lower()}.csv"
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            file_path = folder_path / Path(file_name)

            data_frame.to_csv(file_path, index=False)
            file_paths.append(str(file_path))

        return file_paths

    def get_realization(self, realization_id: int) -> list[DataFrame]:
        return self._sumo_interface.get_realization(realization_id)

    def get_blob(self, realization_id: int) -> list[BytesIO]:
        return self._sumo_interface.get_blob(realization_id)

    @staticmethod
    def _validate_object(data_frame: DataFrame, schema_url: str) -> None:
        """Validate the standard result objects against its schema"""

        validator_interface = SchemaValidationInterface()
        validator_interface.validate_against_schema(
            schema_url=schema_url, data=data_frame.to_dict(orient="records")
        )


class InplaceVolumesLoader(StandardResultsLoader[T]):
    """Class representing a set of Inplace Volumes standard results in fmu-dataio."""

    def __init__(self, case_id: UUID, ensemble_name: str):
        super().__init__(
            case_id, ensemble_name, enums.StandardResultName.inplace_volumes
        )


class FieldOutlineLoader(StandardResultsLoader[T]):
    """Class representing a set of Field Outline standard results in fmu-dataio."""

    def __init__(self, case_id: UUID, ensemble_name: str) -> None:
        super().__init__(case_id, ensemble_name, enums.StandardResultName.field_outline)


@experimental
def load_inplace_volumes(case_id: UUID, ensemble_name: str) -> InplaceVolumesLoader:
    """Simplified interface to load inplace volumes standard results from Sumo."""
    return InplaceVolumesLoader(case_id, ensemble_name)


@experimental
def load_field_outlines(case_id: UUID, ensemble_name: str) -> FieldOutlineLoader:
    """Simplified interface to load field outline standard results from Sumo."""
    return FieldOutlineLoader(case_id, ensemble_name)
