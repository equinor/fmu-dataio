from uuid import UUID

import numpy as np

from fmu.dataio.export._decorators import experimental
from fmu.dataio.external_interfaces.schema_validation_interface import (
    SchemaValidationInterface,
)
from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface
from fmu.sumo.explorer.objects import Surface, Table


@experimental
def load_structure_depth_surfaces(sumo_case_id: UUID) -> list[dict]:
    """Simplified interface to load structure depth surfaces
    standard results from Sumo."""

    structure_depth_surfaces_standard_results: list[Surface] = SumoExplorerInterface(
        case_id=sumo_case_id,
    ).get_structure_depth_surfaces_standard_results()

    validator_service = SchemaValidationInterface()
    for structure_depth_surface in structure_depth_surfaces_standard_results:
        # Should we return the metadata which validates OK or fail all?
        # Failing all for now
        metadata = structure_depth_surface.metadata
        validator_service.validate_against_schema(
            schema_url=metadata["$schema"], data=metadata
        )

    return structure_depth_surfaces_standard_results


@experimental
def load_inplace_volumes(sumo_case_id: UUID) -> list[dict]:
    """Simplified interface to load inplace volumes standard results from Sumo."""

    inplace_volumes_standard_results: list[Table] = SumoExplorerInterface(
        case_id=sumo_case_id,
    ).get_inplace_volumes_standard_results()

    validator_interface = SchemaValidationInterface()
    for inplace_volume in inplace_volumes_standard_results:
        # Should we return the metadata which validates OK or fail all?
        # Failing all for now

        metadata = inplace_volume.metadata
        validator_interface.validate_against_schema(
            schema_url=metadata["$schema"], data=metadata
        )

        table_data_frame = (
            inplace_volume.to_pandas().replace(np.nan, None).to_dict(orient="records")
        )

        validator_interface.validate_against_schema(
            schema_url=metadata["data"]["product"]["file_schema"]["url"],
            data=table_data_frame,
        )

    return inplace_volumes_standard_results
