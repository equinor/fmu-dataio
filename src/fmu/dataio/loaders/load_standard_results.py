from dataclasses import dataclass, field
from uuid import UUID

import jsonschema
import jsonschema.protocols
import requests  # type: ignore

from fmu.dataio.export._decorators import experimental
from fmu.external.sumo_explorer_interface import SumoExplorerInterface


@dataclass
class _SchemaValidatorService:
    _cached_schemas: dict = field(default_factory=dict)  # Alternative 1
    _cached_validator: dict = field(default_factory=dict)  # Alternative 2

    # Alterntive 1: Cached schemas. Cleaner, but takes ~25 seconds for 100 objects
    def _validate_against_schema_alt1(self, metadata: dict) -> bool | Exception:
        schema_version = metadata["version"]

        if schema_version not in self._cached_schemas:
            schema_url = metadata["$schema"]

            response: requests.Response
            try:
                response = requests.get(schema_url)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                # Should we log some information about the error here?
                raise SystemExit(err) from err

            self._cached_schemas[schema_version] = response.json()

        json_schema_standard_result = self._cached_schemas[schema_version]

        jsonschema.validate(
            schema=json_schema_standard_result,
            instance=metadata,
        )

        return True

    # Alternative 2. Cached validator. Faster, takes ~3.5 seconds for 100 objects
    def _validate_against_schema_alt2(self, metadata: dict) -> bool | Exception:
        schema_version = metadata["version"]
        if schema_version not in self._cached_validator:
            schema_url = metadata["$schema"]

            response: requests.Response
            try:
                response = requests.get(schema_url)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                # Should we log some information about the error here?
                raise SystemExit(err) from err

            json_schema_standard_result = response.json()
            jsonschema.Draft202012Validator.check_schema(json_schema_standard_result)
            self._cached_validator[schema_version] = jsonschema.Draft202012Validator(
                json_schema_standard_result
            )

        json_schema_validator = self._cached_validator[schema_version]

        if not json_schema_validator.is_valid(instance=metadata):
            # Run the full validation to get the validation error
            jsonschema.validate(
                schema=json_schema_validator.schema,
                instance=metadata,
            )

        return True


@experimental
def load_structure_depth_surfaces(sumo_case_id: UUID) -> list[dict]:
    """Simplified interface to load structure depth surfaces from Sumo."""

    surface_depth_metadata = SumoExplorerInterface(
        case_id=sumo_case_id,
    ).get_surface_depth_metadata()

    structure_depth_surfaces_stadard_results: list[dict] = []
    validator_service = _SchemaValidatorService()
    for metadata in surface_depth_metadata:
        if validator_service._validate_against_schema_alt2(metadata):
            structure_depth_surfaces_stadard_results.append(metadata)

    return structure_depth_surfaces_stadard_results


@experimental
def load_inplace_volumes(sumo_case_id: UUID) -> list[dict]:
    """Simplified interface to load inplace volumes from Sumo."""

    volume_table_metadata = SumoExplorerInterface(
        case_id=sumo_case_id,
    ).get_volume_table_metadata()

    validator_service = _SchemaValidatorService()
    inplace_volumes_standard_results: list[dict] = []
    for metadata in volume_table_metadata:
        if validator_service._validate_against_schema_alt2(metadata):
            inplace_volumes_standard_results.append(metadata)

    return inplace_volumes_standard_results
