"""Test the surface_io module."""
from collections import OrderedDict
import pytest

import fmu.dataio as fio
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


@pytest.mark.parametrize(
    "name, tagname, t1, t2, loc, expectedstem, expectedpath",
    [
        (
            "some",
            "case1",
            None,
            None,
            "surface",
            "some--case1",
            "maps",
        ),
        (
            "some",
            "case2",
            None,
            None,
            "grid",
            "some--case2",
            "grids",
        ),
        (
            "some",
            None,
            None,
            None,
            "wrong",
            "some",
            "other",
        ),
        (
            "some",
            None,
            20200101,
            None,
            "grid",
            "some--20200101",
            "grids",
        ),
        (
            "some",
            "case8",
            20200101,
            20400909,
            "grid",
            "some--case8--20400909_20200101",
            "grids",
        ),
    ],
)
def test_utils_construct_file(
    tmp_path, name, tagname, t1, t2, loc, expectedstem, expectedpath
):
    """Testing construct file."""
    stem, dest = _utils.construct_filename(
        name, tagname=tagname, loc=loc, t1=t1, t2=t2, outroot=tmp_path
    )

    assert stem == expectedstem
    assert dest.resolve() == (tmp_path / expectedpath).resolve()


def test_utils_verify_path():
    """Testing veriy the path."""
    ed = fio.ExportData(
        config=CFG,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="any",
        verbosity="DEBUG",
        workflow="dummy",
    )

    path, metapath, relpath, abspath = _utils.verify_path(
        ed,
        "tmp/share/results",
        "somefile",
        ".myext",
        dryrun=True,
    )
    print()

    print(path)
    print(metapath)
    print(relpath)
    print(abspath)


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
    """Testing parsing of paramaters.txt to JSON"""

    ptext = "tests/data/drogon/ertrun1/realization-1/iter-0/parameters.txt"

    res = _utils.read_parameters_txt(ptext)

    assert res["SENSNAME"] == "rms_seed"
    assert res["GLOBVAR"]["VOLON_PERMH_CHANNEL"] == 1100
