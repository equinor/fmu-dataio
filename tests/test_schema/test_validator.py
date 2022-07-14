"""Test the JSON Schema validator."""

import pytest

import logging
import requests

from pathlib import PurePath, Path

from fmu.dataio._validator import _Validator

import jsonschema

logger = logging.getLogger(__name__)

ROOTPWD = Path(".").absolute()


def test_validator_initialization():
    """Initialize the _Validate class."""

    vdr = _Validator()

    _schema = {"mytag": {"type": "string"}}
    vdr = _Validator(global_schema=_schema)

    assert vdr._global_schema == _schema


def test_is_metadata_file():
    """Test the _is_metadata_file private method."""
    vdr = _Validator()
    imf = vdr._is_metadata_file  # short-form
    assert imf("/absolute/path/to/file.gri") == False
    assert imf("/absolute/path/to/.file.gri.yml") == True
    assert imf("/absolute/path/to/.file.gri.yaml") == True
    assert imf("relative/path/to/file.gri") == False
    assert imf("relative/path/to/.file.gri.yml") == True
    assert imf(".file.gri.yml") == True
    assert imf("file.gri") == False


def test_create_results():
    """Test the _create_results private method."""
    vdr = _Validator()
    _result = vdr._create_results(False, "some reason")
    assert _result == {"valid": False, "reason": "some reason"}

    _result = vdr._create_results(True)
    assert _result == {"valid": True, "reason": None}


def test_preflight_validation():
    """Test the _preflight_validation private method."""

    vdr = _Validator()

    # no $schema
    instance = {"some": "metadata"}
    valid, reason = vdr._preflight_validation(instance)
    assert valid == False

    # with $schema
    instance = {"some": "metadata", "$schema": "some_url"}
    valid, reason = vdr._preflight_validation(instance)
    assert valid == True


def test_parse_schema():
    """Test the parse_schema private method."""

    vdr = _Validator()
    a_dict = {"mytag": {"type": "string"}}
    a_url = _fmu_schema_url()
    a_path = _fmu_schema_path()

    # from dict
    assert vdr._parse_schema(a_dict) == a_dict

    # from url
    res = vdr._parse_schema(a_url)
    assert isinstance(res, dict)
    assert "$id" in res

    # from path
    res = vdr._parse_schema(a_path)
    assert isinstance(res, dict)
    assert "$id" in res

    # caching
    vdr._parse_schema(a_path)
    vdr._cached_schema["schema"]["a trace"] = "is left"
    vdr._parse_schema(a_path)
    assert "a trace" in vdr._cached_schema["schema"]

    vdr._cached_schema["reference"] = "not the same as before"
    vdr._parse_schema(a_path)
    assert "a trace" not in vdr._cached_schema["schema"]


def test_validate():
    """Test the _validate private method."""

    # shall be valid
    instance = {"mytag": "myvalue"}
    schema = {"properties": {"mytag": {"type": "string"}}}

    # validate directly first to confirm assumptions
    assert jsonschema.validate(instance, schema) is None

    # now validate with our code
    vdr = _Validator(global_schema=schema)
    assert vdr._validate(instance, schema) == {"valid": True, "reason": None}

    vdr = _Validator(global_schema=schema)
    assert vdr._validate(instance, vdr._global_schema) == {
        "valid": True,
        "reason": None,
    }

    vdr = _Validator()
    assert vdr._validate(instance, schema) == {"valid": True, "reason": None}

    # shall be not valid
    instance = {"mytag": 123.0}
    schema = {"properties": {"mytag": {"type": "string"}}}

    # validate directly first to confirm assumptions
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance, schema)

    # now validate with our code
    vdr = _Validator(global_schema=schema)
    res = vdr._validate(instance, schema)
    assert res["valid"] == False
    assert "reason" in res
    assert "123.0 is not of type 'string'" in res["reason"]


# ================
# tmp fixtures
# ================


def _fmu_schema_url():
    """Return the schema url."""
    protocol = "https"
    subdomain = "main-fmu-schemas-dev"
    domain = "radix.equinor.com"

    version = "0.8.0"
    schema = "fmu_results.json"
    path = f"schemas/{version}/{schema}"

    return f"{protocol}://{subdomain}.{domain}/{path}"


def _fmu_schema_path():
    """Return the filepath to the fmu_results schema."""
    return str(PurePath(ROOTPWD, "schema/definitions/0.8.0/schema/fmu_results.json"))
