from uuid import UUID

from fmu.dataio.export._decorators import experimental
from fmu.external.schema_validation_interface import SchemaValidationInterface
from fmu.external.sumo_explorer_interface import SumoExplorerInterface


@experimental
def load_structure_depth_surfaces(sumo_case_id: UUID) -> list[dict]:
    """Simplified interface to load structure depth surfaces
    standard results from Sumo."""

    structure_depth_surfaces_standard_results = SumoExplorerInterface(
        case_id=sumo_case_id,
    ).get_structure_depth_surfaces_standard_results()

    validator_service = SchemaValidationInterface()
    for metadata in structure_depth_surfaces_standard_results:
        # Should we return the metadata which validates OK or fail all?
        # Failing all for now
        validator_service.validate_against_schema(metadata)

    return structure_depth_surfaces_standard_results


@experimental
def load_inplace_volumes(sumo_case_id: UUID) -> list[dict]:
    """Simplified interface to load inplace volumes standard results from Sumo."""

    inplace_volumes_standard_results = SumoExplorerInterface(
        case_id=sumo_case_id,
    ).get_inplace_volumes_standard_results()

    validator_interface = SchemaValidationInterface()
    for metadata in inplace_volumes_standard_results:
        # Should we return the metadata which validates OK or fail all?
        # Failing all for now
        validator_interface.validate_against_schema(metadata)

    return inplace_volumes_standard_results
