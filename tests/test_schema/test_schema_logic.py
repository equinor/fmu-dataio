"""Test the schema"""
import logging
from pathlib import Path, PurePath
import datetime
from copy import deepcopy

import yaml
import json
import jsonschema

import pytest


# pylint: disable=no-member

logger = logging.getLogger(__name__)

ROOTPWD = Path(".").absolute()


def test_schema_basic_json_syntax():
    """Confirm that schemas are valid JSON"""

    # find and parse all schema files. Listing to catch if none are found.
    schema_file_paths = list(ROOTPWD.glob("schema/definitions/*/schema/*.json"))

    # check that schemas are there
    assert len(schema_file_paths) > 0

    for schema_file_path in schema_file_paths:
        _parse_json(schema_file_path)


def test_schema_example_filenames():
    """Assert that all examples are .yml, not .yaml"""

    # find and parse all example files. Listing to catch if none are found.
    filenames = list(ROOTPWD.glob("schema/definitions/*/examples/*.*"))

    # check that examples are there
    assert len(filenames) > 0

    for filename in filenames:
        assert filename.name.endswith(".yml"), filename


def test_schema_080_validate_examples_as_is():
    """Confirm that examples are valid against the schema"""

    # parse the schema
    schema = _parse_json(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    examples = [
        _parse_yaml(str(path))
        for path in ROOTPWD.glob("schema/definitions/0.8.0/examples/*.yml")
    ]

    for example in examples:
        jsonschema.validate(instance=example, schema=schema)


def test_schema_080_file_block():
    """Test variations on the file block."""

    # parse the schema
    schema = _parse_json(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    metadata = _parse_yaml(
        ROOTPWD / "schema/definitions/0.8.0/examples/surface_depth.yml"
    )

    # shall validate as-is
    jsonschema.validate(instance=metadata, schema=schema)

    # shall validate without absolute_path
    del metadata["file"]["absolute_path"]
    jsonschema.validate(instance=metadata, schema=schema)

    # md5 checksum shall be a string
    metadata["file"]["checksum_md5"] = 123.4
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=metadata, schema=schema)

    # shall not validate without checksum_md5
    del metadata["file"]["checksum_md5"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=metadata, schema=schema)

    # shall validate when checksum is put back in
    metadata["file"]["checksum_md5"] = "somechecksum"
    jsonschema.validate(instance=metadata, schema=schema)

    # shall not validate without relative_path
    del metadata["file"]["relative_path"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=metadata, schema=schema)


def test_schema_080_logic_case():
    """Asserting validation failure when illegal contents in case example"""

    # parse the schema and one example
    schema = _parse_json(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    example = _parse_yaml(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/examples/case.yml"))
    )

    # assert validation with no changes
    jsonschema.validate(instance=example, schema=schema)

    # assert validation error when "fmu" is missing
    _example = deepcopy(example)
    del _example["fmu"]

    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=schema)

    # assert validation error when "fmu.model" is missing
    _example = deepcopy(example)
    del _example["fmu"]["model"]

    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=schema)


def test_schema_080_logic_fmu_block_aggregation_realization():
    """Test that fmu.realization and fmu.aggregation are not allowed at the same time"""

    # parse the schema and polygons
    schema = _parse_json(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    metadata = _parse_yaml(
        str(
            PurePath(
                ROOTPWD,
                "schema/definitions/0.8.0/examples/surface_depth.yml",
            )
        )
    )

    # check that assumptions for the test is true
    assert "realization" in metadata["fmu"]
    assert "aggregation" not in metadata["fmu"]

    # assert validation as-is
    jsonschema.validate(instance=metadata, schema=schema)

    # add aggregation, shall fail. Get this from an actual example that validates.
    _metadata_aggregation = _parse_yaml(
        str(
            PurePath(
                ROOTPWD,
                "schema/definitions/0.8.0/examples/aggregated_surface_depth.yml",
            )
        )
    )

    metadata["fmu"]["aggregation"] = _metadata_aggregation["fmu"]["aggregation"]

    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=metadata, schema=schema)


def test_schema_080_logic_data_top_base():
    """Test require data.top and data.base.

    * Require both data.top and data.base, or none.
    """

    # parse the schema and metadata example
    schema = _parse_json(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    metadata = _parse_yaml(
        str(
            PurePath(
                ROOTPWD,
                "schema/definitions/0.8.0/examples/surface_seismic_amplitude.yml",
            )
        )
    )

    # check that assumptions for the test is true
    assert "top" in metadata["data"]
    assert "base" in metadata["data"]

    # assert validation as-is
    jsonschema.validate(instance=metadata, schema=schema)

    # remove "top" - shall fail
    _metadata = deepcopy(metadata)
    del _metadata["data"]["top"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=schema)

    # remove "base" - shall fail
    _metadata = deepcopy(metadata)
    del _metadata["data"]["base"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=schema)

    # remove both - shall pass
    del _metadata["data"]["top"]
    assert "top" not in _metadata["data"]  # test assumption
    assert "base" not in _metadata["data"]  # test assumption
    jsonschema.validate(instance=_metadata, schema=schema)


def test_schema_080_logic_field_outline():
    """Test content-specific rule

    When content == field_outline, require the field_outline field
    """

    # parse the schema and polygons
    schema = _parse_json(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    metadata = _parse_yaml(
        str(
            PurePath(
                ROOTPWD,
                "schema/definitions/0.8.0/examples/polygons_field_outline.yml",
            )
        )
    )

    # check that assumptions for the test is true
    assert metadata["data"]["content"] == "field_outline"
    assert "field_outline" in metadata["data"]

    # assert validation as-is
    jsonschema.validate(instance=metadata, schema=schema)

    # assert failure when content is field_outline and fluid_contact is missing
    _metadata = deepcopy(metadata)
    del _metadata["data"]["field_outline"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=schema)


def test_schema_080_logic_fluid_contact():
    """Test content-specific rule

    When content == fluid_contact, require the fluid_contact field
    """

    # parse the schema and polygons
    schema = _parse_json(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    metadata = _parse_yaml(
        str(
            PurePath(
                ROOTPWD,
                "schema/definitions/0.8.0/examples/surface_fluid_contact.yml",
            )
        )
    )

    # check that assumptions for the test is true
    assert metadata["data"]["content"] == "fluid_contact"
    assert "fluid_contact" in metadata["data"]

    # assert failure when content is fluid_contact and fluid_contact block missing
    _metadata = deepcopy(metadata)
    del _metadata["data"]["fluid_contact"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=schema)


def test_schema_080_masterdata_smda():
    """Test schema logic for masterdata.smda"""

    # parse the schema and one example
    schema = _parse_json(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    example = _parse_yaml(
        str(PurePath(ROOTPWD, "schema/definitions/0.8.0/examples/case.yml"))
    )

    # assert validation with no changes
    jsonschema.validate(instance=example, schema=schema)

    # assert validation error when masterdata block is missing
    _example = deepcopy(example)
    del _example["masterdata"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=schema)

    # assert validation error when masterdata.smda is missing
    # print(example["masterdata"])
    _example = deepcopy(example)
    del _example["masterdata"]["smda"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=schema)

    # assert validation error when missing attribute
    for block in [
        "country",
        "discovery",
        "field",
        "coordinate_system",
        "stratigraphic_column",
    ]:
        _example = deepcopy(example)
        del _example["masterdata"]["smda"][block]
        with pytest.raises(jsonschema.exceptions.ValidationError):
            jsonschema.validate(instance=_example, schema=schema)

    # assert validation error if not correct type
    for block, type_ in [
        ("country", list),
        ("discovery", list),
        ("coordinate_system", dict),
        ("stratigraphic_column", dict),
    ]:
        _example = deepcopy(example)
        assert isinstance(_example["masterdata"]["smda"][block], type_)

        _example["masterdata"]["smda"][block] = "somestring"

        with pytest.raises(jsonschema.exceptions.ValidationError):
            jsonschema.validate(instance=_example, schema=schema)


# ==========================================
# Utility functions
# ==========================================


def _parse_json(schema_path):
    """Parse the schema, return JSON"""
    with open(schema_path) as stream:
        data = json.load(stream)

    return data


def _parse_yaml(yaml_path):
    """Parse the filename as json, return data"""
    with open(yaml_path, "r") as stream:
        data = yaml.safe_load(stream)

    data = _isoformat_all_datetimes(data)

    return data


def _isoformat_all_datetimes(data):
    """Recursive function to isoformat all datetimes in a dictionary"""

    if isinstance(data, list):
        data = [_isoformat_all_datetimes(i) for i in data]
        return data

    if isinstance(data, dict):
        for key in data:
            data[key] = _isoformat_all_datetimes(data[key])

    if isinstance(data, datetime.datetime):
        return data.isoformat()

    if isinstance(data, datetime.date):
        return data.isoformat()

    return data
