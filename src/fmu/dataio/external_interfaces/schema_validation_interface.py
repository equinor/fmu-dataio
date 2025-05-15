from functools import lru_cache

import jsonschema
import requests


class SchemaValidationInterface:
    @staticmethod
    @lru_cache
    def _get_validator(schema_url: str) -> jsonschema.Draft202012Validator:
        """
        Get the schema validator to use to validate data objects.
        Use cached validator when present for the requested schema, or
        create a new validator and add it to the cache.
        """

        response: requests.Response

        try:
            response = requests.get(schema_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err) from err

        json_schema = response.json()
        jsonschema.Draft202012Validator.check_schema(json_schema)
        return jsonschema.Draft202012Validator(json_schema)

    def validate_against_schema(
        self, schema_url: str, data: object
    ) -> bool | Exception:
        """Validate the provided data object against the provided schema."""

        json_schema_validator = self._get_validator(schema_url)

        if not json_schema_validator.is_valid(instance=data):
            jsonschema.validate(
                schema=json_schema_validator.schema,
                instance=data,
            )

        return True
