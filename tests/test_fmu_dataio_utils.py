"""Test the surface_io module."""
from collections import OrderedDict

import pandas as pd
import pytest
import xtgeo

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
CFG["access"] = {
    "asset": "Drogon",
    "ssdl": {"access_level": "internal", "some_access_tag": True},
}
CFG["model"] = {"revision": "0.99.0"}


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
        # GEN_KW lookalike
        (
            {"foo:bar": "com1", "hoi:bar": "com2"},
            {"foo": {"bar": "com1"}, "hoi": {"bar": "com2"}},
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


def test_parse_parameters_txt_genkw():
    """Testing parsing of parameters.txt from GEN_KW"""

    ptext = "tests/data/drogon/ertrun1/realization-0/iter-0/parameters_genkw.txt"

    res = _utils.nested_parameters_dict(_utils.read_parameters_txt(ptext))

    assert res["CATEGORY1"]["SOMENAME"] == -0.01


def test_get_object_name():
    """Test the method for getting name from a data object"""

    # surface with no name, shall return None
    surface = xtgeo.RegularSurface(ncol=3, nrow=4, xinc=22, yinc=22, values=0)
    assert _utils.get_object_name(surface) is None

    # surface with name, shall return the name
    surface.name = "MySurfaceName"
    assert _utils.get_object_name(surface) == "MySurfaceName"

    # dataframe: shall return None
    table = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    assert _utils.get_object_name(table) is None

    # polygons with no name, shall return None
    poly = xtgeo.Polygons([(123.0, 345.0, 222.0, 0), (123.0, 345.0, 222.0, 0)])
    assert _utils.get_object_name(poly) is None

    # polygons with name, shall return name
    poly.name = "MyPolygonsName"
    assert _utils.get_object_name(poly) == "MyPolygonsName"

    # points with no name, shall return None
    points = xtgeo.Points(
        [
            (1.0, 2.0, 3.0),
            (1.5, 2.5, 3.5),
            (1.2, 2.2, 3.1),
            (1.1, 2.0, 3.0),
            (1.1, 2.0, 3.0),
            (1.1, 2.0, 3.0),
            (1.1, 2.0, 3.0),
        ]
    )
    assert _utils.get_object_name(points) is None

    # points with name, shall return name
    points.name = "MyPointsName"
    assert _utils.get_object_name(points) == "MyPointsName"

    # grid with no name, shall return None
    grid = xtgeo.create_box_grid((2, 4, 6))
    assert _utils.get_object_name(grid) is None

    # grid with name, shall return name
    grid.name = "MyGridName"
    assert _utils.get_object_name(grid) == "MyGridName"
