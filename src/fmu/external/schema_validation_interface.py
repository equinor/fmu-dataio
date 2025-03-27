from dataclasses import dataclass
from functools import lru_cache

import jsonschema
import requests  # type: ignore


@dataclass
class SchemaValidationInterface:
    @staticmethod
    @lru_cache
    def _get_cached_validator(schema_url: str) -> jsonschema.Draft202012Validator:
        response: requests.Response

        try:
            response = requests.get(schema_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err) from err

        json_schema_fmu_result = response.json()
        jsonschema.Draft202012Validator.check_schema(json_schema_fmu_result)
        return jsonschema.Draft202012Validator(json_schema_fmu_result)

    def validate_against_schema(self, metadata: dict) -> bool | Exception:
        schema_url = metadata["$schema"]
        json_schema_validator = self._get_cached_validator(schema_url)

        if not json_schema_validator.is_valid(instance=metadata):
            # Run the full validation to raise the validation error
            jsonschema.validate(
                schema=json_schema_validator.schema,
                instance=metadata,
            )

        return True
