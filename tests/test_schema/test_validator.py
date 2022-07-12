"""Test the JSON Schema validator."""

import logging

from fmu.dataio._validator import _Validator

import jsonschema

logger = logging.getLogger(__name__)


def test_validator_initialization():
    """Initialize the _Validate class."""

    vdr = _Validator()


def test_validator_basic_validation():
    """On a minimum schema, test a minimum candidate."""

    instance = {"mytag": "myvalue"}
    schema = {"mytag": {"type": "string"}}

    # validate directly first to confirm assumptions
    assert jsonschema.validate(instance, schema) is None

    # now validate with our code
    vdr = _Validator(schema=schema)
    res = vdr._validate(instance)
    assert res["valid"] == True

    # non-valid example
    instance = {"mytag": 123.0}
    res = vdr._validate(instance)
    assert res["valid"] == False
