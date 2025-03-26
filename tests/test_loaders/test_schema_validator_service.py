import pytest
from jsonschema import ValidationError

import fmu.dataio.loaders.load_standard_results as load_standard_results


def test_validator_valid_metadata(metadata_examples):
    inplace_volumes = metadata_examples["table_inplace_volumes.yml"]
    validator = load_standard_results._SchemaValidatorService()
    assert validator._validate_against_schema_alt2(inplace_volumes)


def test_validator_invalid_metadata():
    metadata = {
        "$schema": "https://main-fmu-schemas-prod.radix.equinor.com/schemas/0.8.0/fmu_results.json",
        "version": "0.8.0",
    }

    validator = load_standard_results._SchemaValidatorService()
    with pytest.raises(ValidationError):
        validator._validate_against_schema_alt2(metadata)
