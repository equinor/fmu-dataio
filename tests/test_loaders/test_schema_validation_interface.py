from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests
from jsonschema import ValidationError

from fmu.dataio.external_interfaces.schema_validation_interface import (
    SchemaValidationInterface,
)

VOLUME_PATH = Path("tests/data/drogon/tabular/volumes/geogrid.csv").absolute()

SCHEMA_URL_INPLACE_VOLUME = "https://main-fmu-schemas-prod.radix.equinor.com/schemas/file_formats/0.1.0/inplace_volumes.json"


def schema_exists(schema_url):
    """Check if the schema exists by making a HEAD request."""
    try:
        response = requests.head(schema_url)
        return response.status_code == 200
    except requests.RequestException:
        return False


def test_validator_when_valid_metadata(metadata_examples):
    inplace_volumes = metadata_examples["table_inplace_volumes.yml"]
    schema_url = inplace_volumes["$schema"]

    # for PR's bumping a schema version the schema does not exist yet
    if not schema_exists(schema_url):
        pytest.skip(f"Schema at {schema_url} does not exist.")

    validator = SchemaValidationInterface()
    validator._get_validator.cache_clear()

    assert validator.validate_against_schema(
        schema_url=schema_url, data=inplace_volumes
    )


def test_validator_when_invalid_metadata():
    metadata = {
        "$schema": "https://main-fmu-schemas-prod.radix.equinor.com/schemas/0.8.0/fmu_results.json",
        "version": "0.8.0",
    }

    validator = SchemaValidationInterface()
    validator._get_validator.cache_clear()

    with pytest.raises(ValidationError):
        validator.validate_against_schema(schema_url=metadata["$schema"], data=metadata)


def test_validator_when_valid_payload():
    data_frame = (
        pd.read_csv(VOLUME_PATH).replace(np.nan, None).to_dict(orient="records")
    )

    validator = SchemaValidationInterface()
    validator._get_validator.cache_clear()

    assert validator.validate_against_schema(
        schema_url=SCHEMA_URL_INPLACE_VOLUME, data=data_frame
    )


def test_validator_when_ivalid_payload():
    data_frame = (
        pd.read_csv(VOLUME_PATH).replace(np.nan, None).to_dict(orient="records")
    )

    del data_frame[0]["FLUID"]

    validator = SchemaValidationInterface()
    validator._get_validator.cache_clear()

    with pytest.raises(ValidationError, match="'FLUID' is a required property"):
        validator.validate_against_schema(
            schema_url=SCHEMA_URL_INPLACE_VOLUME, data=data_frame
        )


def test_caching(metadata_examples):
    inplace_volumes_metadata = metadata_examples["table_inplace_volumes.yml"]
    inplace_volumes_metadata2 = inplace_volumes_metadata
    schema_url_fmu_results = inplace_volumes_metadata["$schema"]

    # for PR's bumping a schema version the schema does not exist yet
    if not schema_exists(schema_url_fmu_results):
        pytest.skip(f"Schema at {schema_url_fmu_results} does not exist.")

    validator = SchemaValidationInterface()
    validator._get_validator.cache_clear()

    # Validate against fmu results schema and assert schema is added to cache
    validator.validate_against_schema(schema_url_fmu_results, inplace_volumes_metadata)
    cache_info = SchemaValidationInterface._get_validator.cache_info()
    assert cache_info.misses == 1
    assert cache_info.hits == 0

    # Validate against fmu results schema again and assert cached schema is used
    validator.validate_against_schema(schema_url_fmu_results, inplace_volumes_metadata2)
    cache_info = SchemaValidationInterface._get_validator.cache_info()
    assert cache_info.misses == 1
    assert cache_info.hits == 1

    # Validate against inplace volume schema and assert schema is added to cache
    inplace_volumes_payload = (
        pd.read_csv(VOLUME_PATH).replace(np.nan, None).to_dict(orient="records")
    )
    validator.validate_against_schema(
        SCHEMA_URL_INPLACE_VOLUME, inplace_volumes_payload
    )
    cache_info = SchemaValidationInterface._get_validator.cache_info()
    assert cache_info.hits == 1
    assert cache_info.misses == 2
