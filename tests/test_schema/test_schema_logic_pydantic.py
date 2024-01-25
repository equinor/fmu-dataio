"""Test the schema"""
import logging
from copy import deepcopy

import jsonschema
import pytest
from conftest import metadata_examples
from fmu.dataio._definitions import ALLOWED_CONTENTS
from fmu.dataio.models.meta import Root, dump
from fmu.dataio.models.meta.enums import ContentEnum

# pylint: disable=no-member

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def pydantic_schema():
    return dump()


@pytest.mark.parametrize("file, example", metadata_examples().items())
def test_schema_example_filenames(file, example):
    """Assert that all examples are .yml, not .yaml"""
    assert file.endswith(".yml")


# ======================================================================================
# 0.8.0
# ======================================================================================


@pytest.mark.parametrize("file, example", metadata_examples().items())
def test_jsonschema_validate(pydantic_schema, file, example):
    """Confirm that examples are valid against the schema"""
    jsonschema.validate(instance=example, schema=pydantic_schema)


@pytest.mark.parametrize("file, example", metadata_examples().items())
def test_pydantic_model_validate(pydantic_schema, file, example):
    """Confirm that examples are valid against the schema"""
    Root.model_validate(example)


def test_pydantic_schema_file_block(pydantic_schema, metadata_examples):
    """Test variations on the file block."""

    # get a specific example
    example = metadata_examples["surface_depth.yml"]

    # Root.model_validate(example)
    # shall validate as-is
    jsonschema.validate(instance=example, schema=pydantic_schema)

    # shall validate without absolute_path
    _example = deepcopy(example)
    del _example["file"]["absolute_path"]
    jsonschema.validate(instance=_example, schema=pydantic_schema)

    # md5 checksum shall be a string
    _example["file"]["checksum_md5"] = 123.4
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=pydantic_schema)

    # shall not validate without checksum_md5
    del _example["file"]["checksum_md5"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=pydantic_schema)

    # shall validate when checksum is put back in
    _example["file"]["checksum_md5"] = "somechecksum"
    jsonschema.validate(instance=_example, schema=pydantic_schema)

    # shall not validate without relative_path
    del _example["file"]["relative_path"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=pydantic_schema)


def test_pydantic_schema_logic_case(pydantic_schema, metadata_examples):
    """Asserting validation failure when illegal contents in case example"""

    example = metadata_examples["case.yml"]

    # assert validation with no changes
    jsonschema.validate(instance=example, schema=pydantic_schema)

    # assert validation error when "fmu" is missing
    _example = deepcopy(example)
    del _example["fmu"]

    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=pydantic_schema)

    # assert validation error when "fmu.model" is missing
    _example = deepcopy(example)
    del _example["fmu"]["model"]

    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=pydantic_schema)


def test_pydantic_schema_logic_fmu_block_aggr_real(pydantic_schema, metadata_examples):
    """Test that fmu.realization and fmu.aggregation are not allowed at the same time"""

    metadata = deepcopy(metadata_examples["surface_depth.yml"])
    # check that assumptions for the test is true
    assert "realization" in metadata["fmu"]
    assert "aggregation" not in metadata["fmu"]

    # assert validation as-is
    jsonschema.validate(instance=metadata, schema=pydantic_schema)

    # add aggregation, shall fail. Get this from an actual example that validates.
    _metadata_aggregation = metadata_examples["aggregated_surface_depth.yml"]
    metadata["fmu"]["aggregation"] = _metadata_aggregation["fmu"]["aggregation"]

    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=metadata, schema=pydantic_schema)


def test_pydantic_schema_logic_data_top_base(pydantic_schema, metadata_examples):
    """Test require data.top and data.base.

    * Require both data.top and data.base, or none.
    """

    metadata = metadata_examples["surface_seismic_amplitude.yml"]

    # check that assumptions for the test is true
    assert "top" in metadata["data"]
    assert "base" in metadata["data"]

    # assert validation as-is
    jsonschema.validate(instance=metadata, schema=pydantic_schema)

    # remove "top" - shall fail
    _metadata = deepcopy(metadata)
    del _metadata["data"]["top"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=pydantic_schema)

    # remove "base" - shall fail
    _metadata = deepcopy(metadata)
    del _metadata["data"]["base"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=pydantic_schema)

    # remove both - shall pass
    del _metadata["data"]["top"]
    assert "top" not in _metadata["data"]  # test assumption
    assert "base" not in _metadata["data"]  # test assumption
    jsonschema.validate(instance=_metadata, schema=pydantic_schema)


def test_pydantic_schema_logic_field_outline(pydantic_schema, metadata_examples):
    """Test content-specific rule.

    When content == field_outline, require the field_outline field
    """

    metadata = metadata_examples["polygons_field_outline.yml"]

    # check that assumptions for the test is true
    assert metadata["data"]["content"] == "field_outline"
    assert "field_outline" in metadata["data"]

    # assert validation as-is
    jsonschema.validate(instance=metadata, schema=pydantic_schema)

    # assert failure when content is field_outline and fluid_contact is missing
    _metadata = deepcopy(metadata)
    del _metadata["data"]["field_outline"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=pydantic_schema)


def test_pydantic_schema_logic_field_region(pydantic_schema, metadata_examples):
    """Test content-specific rule: field_region

    When content == field_outline, require the data.field_region field.
    """

    metadata = metadata_examples["polygons_field_region.yml"]

    # check assumptions
    assert metadata["data"]["content"] == "field_region"
    assert "field_region" in metadata["data"]
    assert "id" in metadata["data"]["field_region"]
    jsonschema.validate(instance=metadata, schema=pydantic_schema)

    # assert that data.field_region is required
    _metadata = deepcopy(metadata)
    del _metadata["data"]["field_region"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=pydantic_schema)

    # validation of data.field_region
    _metadata = deepcopy(metadata)
    del _metadata["data"]["field_region"]["id"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=pydantic_schema)

    _metadata = deepcopy(metadata)
    _metadata["data"]["field_region"]["id"] = "NotANumber"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=pydantic_schema)


def test_pydantic_schema_logic_fluid_contact(pydantic_schema, metadata_examples):
    """Test content-specific rule.

    When content == fluid_contact, require the fluid_contact field
    """

    # parse the schema and polygons
    metadata = metadata_examples["surface_fluid_contact.yml"]

    # check that assumptions for the test is true
    assert metadata["data"]["content"] == "fluid_contact"
    assert "fluid_contact" in metadata["data"]

    # assert failure when content is fluid_contact and fluid_contact block missing
    _metadata = deepcopy(metadata)
    del _metadata["data"]["fluid_contact"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_metadata, schema=pydantic_schema)


def test_pydantic_schema_masterdata_smda(pydantic_schema, metadata_examples):
    """Test schema logic for masterdata.smda."""

    example = metadata_examples["case.yml"]

    # assert validation with no changes
    jsonschema.validate(instance=example, schema=pydantic_schema)

    # assert validation error when masterdata block is missing
    _example = deepcopy(example)
    del _example["masterdata"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=pydantic_schema)

    # assert validation error when masterdata.smda is missing
    # print(example["masterdata"])
    _example = deepcopy(example)
    del _example["masterdata"]["smda"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=_example, schema=pydantic_schema)

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
            jsonschema.validate(instance=_example, schema=pydantic_schema)

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
            jsonschema.validate(instance=_example, schema=pydantic_schema)


def test_pydantic_schema_data_time(pydantic_schema, metadata_examples):
    """Test schema logic for data.time."""

    # fetch one example that contains the data.time element
    example = metadata_examples["surface_seismic_amplitude.yml"]
    assert "time" in example["data"]

    # assert validation with no changes
    jsonschema.validate(instance=example, schema=pydantic_schema)

    # valid when data.time is missing
    _example = deepcopy(example)
    del _example["data"]["time"]
    jsonschema.validate(instance=_example, schema=pydantic_schema)

    # valid when only t0
    _example = deepcopy(example)
    del _example["data"]["time"]["t1"]
    assert "t0" in _example["data"]["time"]  # test assumption
    jsonschema.validate(instance=_example, schema=pydantic_schema)

    # valid without labels
    _example = deepcopy(example)
    del _example["data"]["time"]["t0"]["label"]
    jsonschema.validate(instance=_example, schema=pydantic_schema)

    # NOT valid when other types
    for testvalue in [
        [{"t0": "2020-10-28T14:28:02", "label": "mylabel"}],
        "2020-10-28T14:28:02",
        123,
        123.4,
    ]:
        _example = deepcopy(example)
        _example["data"]["time"] = testvalue
        with pytest.raises(jsonschema.exceptions.ValidationError):
            jsonschema.validate(instance=_example, schema=pydantic_schema)


def test_schema_logic_classification(pydantic_schema, metadata_examples):
    """Test the classification of individual files."""

    # fetch example
    example = deepcopy(metadata_examples["surface_depth.yml"])

    # assert validation with no changes
    jsonschema.validate(instance=example, schema=pydantic_schema)

    # assert "internal" and "restricted" validates
    example["access"]["classification"] = "internal"
    jsonschema.validate(instance=example, schema=pydantic_schema)

    example["access"]["classification"] = "restricted"
    jsonschema.validate(instance=example, schema=pydantic_schema)

    # assert erroneous value does not validate
    example["access"]["classification"] = "open"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=example, schema=pydantic_schema)


def test_schema_logic_data_spec(pydantic_schema, metadata_examples):
    """Test schema logic for data.spec"""

    # fetch surface example
    example_surface = deepcopy(metadata_examples["surface_depth.yml"])

    # assert validation with no changes
    jsonschema.validate(instance=example_surface, schema=pydantic_schema)

    # assert data.spec required when class == surface
    del example_surface["data"]["spec"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=example_surface, schema=pydantic_schema)

    # fetch table example
    example_table = deepcopy(metadata_examples["table_inplace.yml"])

    # assert validation with no changes
    jsonschema.validate(instance=example_table, schema=pydantic_schema)

    # assert data.spec required when class == table
    del example_table["data"]["spec"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=example_table, schema=pydantic_schema)

    # fetch dictionary example
    example_dict = deepcopy(metadata_examples["dictionary_parameters.yml"])

    # assert data.spec is not present
    with pytest.raises(KeyError):
        example_dict["data"]["spec"]

    # assert data.spec not required when class === dictionary
    jsonschema.validate(instance=example_dict, schema=pydantic_schema)


def test_schema_logic_content_whitelist(pydantic_schema, metadata_examples):
    """Test that validation fails when value of data.content is not in
    the whitelist."""

    # fetch surface example
    example_surface = deepcopy(metadata_examples["surface_depth.yml"])

    # assert validation with no changes
    jsonschema.validate(instance=example_surface, schema=pydantic_schema)

    # shall fail when content is not in whitelist
    example_surface["data"]["content"] = "not_valid_content"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=example_surface, schema=pydantic_schema)


def test_schema_content_synch_with_code():
    """Currently, the whitelist for content is maintained both in the schema
    and in the code. This test asserts that list used in the code is in synch
    with schema. Note! This is one-way, and will not fail if additional
    elements are added to the schema only."""

    for allowed_content in ALLOWED_CONTENTS:
        assert allowed_content in {v.name for v in ContentEnum}
