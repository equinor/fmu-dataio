"""Test the surface_io module."""
from collections import OrderedDict

import pytest

import fmu.dataio._utils as _utils

CFG = OrderedDict()
CFG["model"] = {"name": "Test", "revision": "21.0.0"}
CFG["masterdata"] = {
    "smda": {
        "country": [
            {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
        ],
        "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
    }
}


def test_uuid_from_string():
    """Testing that uuid from string is repeatable"""
    string1 = "string1"
    string2 = "string2"

    uuid1 = _utils.uuid_from_string(string1)
    uuid2 = _utils.uuid_from_string(string2)
    uuidx = _utils.uuid_from_string(string1)

    assert uuid1 != uuid2
    assert uuidx == uuid1


def test_parse_parameters_txt():
    """Testing parsing of parameters.txt into a flat dictionary"""

    ptext = "tests/data/drogon/ertrun1/realization-1/iter-0/parameters.txt"

    res = _utils.read_parameters_txt(ptext)

    assert res["SENSNAME"] == "rms_seed"

    # Numbers in strings should be parsed as numbers:
    assert res["GLOBVAR:VOLON_PERMH_CHANNEL"] == 1100


@pytest.mark.parametrize(
    "flat_dict, nested_dict",
    [
        ({}, {}),
        ({"foo": "bar"}, {"foo": "bar"}),
        ({"foo:bar": "com"}, {"foo": {"bar": "com"}}),
        ({"foo:bar:com": "hoi"}, {"foo": {"bar:com": "hoi"}}),
        (
            {"fo": "ba", "foo:bar": "com", "fooo:barr:comm": "hoi"},
            {"fo": "ba", "foo": {"bar": "com"}, "fooo": {"barr:comm": "hoi"}},
        ),
        (
            {"foo:bar": "com", "foo:barr": "comm"},
            {"foo": {"bar": "com", "barr": "comm"}},
        ),
        pytest.param(
            {"foo:bar": "com1", "hoi:bar": "com2"},
            None,
            marks=pytest.mark.xfail(raises=ValueError),
            id="non-unique_keys",
        ),
        pytest.param({"foo:": "com"}, None, marks=pytest.mark.xfail(raises=ValueError)),
    ],
)
def test_nested_parameters(flat_dict, nested_dict):
    assert _utils.nested_parameters_dict(flat_dict) == nested_dict


def test_parse_parameters_txt_justified():
    """Testing parsing of justified parameters.txt into nested dictionary"""

    ptext = "tests/data/drogon/ertrun1/realization-0/iter-0/parameters_justified.txt"

    res = _utils.nested_parameters_dict(_utils.read_parameters_txt(ptext))

    assert res["SENSNAME"] == "rms_seed"
    assert res["GLOBVAR"]["VOLON_PERMH_CHANNEL"] == 1100
    assert res["LOG10_MULTREGT"]["MULT_VALYSAR_THERYS"] == -3.2582
