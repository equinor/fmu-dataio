from copy import deepcopy

import pytest
from jsonschema import ValidationError

from fmu.dataio.external_interfaces.schema_validation_interface import (
    SchemaValidationInterface,
)


def test_validator_valid_metadata(metadata_examples):
    inplace_volumes = metadata_examples["table_inplace_volumes.yml"]

    validator = SchemaValidationInterface()
    validator._get_cached_validator.cache_clear()

    assert validator.validate_against_schema(inplace_volumes)


def test_validator_invalid_metadata():
    metadata = {
        "$schema": "https://main-fmu-schemas-prod.radix.equinor.com/schemas/0.8.0/fmu_results.json",
        "version": "0.8.0",
    }

    validator = SchemaValidationInterface()
    validator._get_cached_validator.cache_clear()

    with pytest.raises(ValidationError):
        validator.validate_against_schema(metadata)


def test_caching(metadata_examples):
    inplace_volumes1 = metadata_examples["table_inplace_volumes.yml"]
    inplace_volumes2 = inplace_volumes1
    inplace_volumes3 = deepcopy(inplace_volumes2)
    inplace_volumes3["$schema"] = (
        "https://main-fmu-schemas-prod.radix.equinor.com/schemas/0.8.0/fmu_results.json"
    )

    validator = SchemaValidationInterface()
    validator._get_cached_validator.cache_clear()

    validator.validate_against_schema(inplace_volumes1)
    validator.validate_against_schema(inplace_volumes2)
    validator.validate_against_schema(inplace_volumes3)

    cache_info = SchemaValidationInterface._get_cached_validator.cache_info()
    assert cache_info.hits == 1
    assert cache_info.misses == 2
