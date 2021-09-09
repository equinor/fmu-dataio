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
        (
            "some.with.dots and some spaces",
            "case8",
            20200101,
            20400909,
            "grid",
            "some_with_dots_and_some_spaces--case8--20400909_20200101",
            "grids",
        ),
    ],
)
def test_utils_construct_filename(
    tmp_path, name, tagname, t1, t2, loc, expectedstem, expectedpath
):
    """Testing construct file."""
    stem, dest = _utils.construct_filename(
        name, pretagname=None, tagname=tagname, loc=loc, t1=t1, t2=t2, outroot=tmp_path
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

    assert str(path).endswith("tmp/share/results/somefile.myext")


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
    """Testing parsing of parameters.txt to JSON"""

    ptext = "tests/data/drogon/ertrun1/realization-1/iter-0/parameters.txt"

    res = _utils.read_parameters_txt(ptext)

    assert res["SENSNAME"] == "rms_seed"
    assert res["GLOBVAR"]["VOLON_PERMH_CHANNEL"] == 1100


def test_parse_parameters_txt_justified():
    """Testing parsing of justified parameters.txt to JSON"""

    ptext = "tests/data/drogon/ertrun1/realization-0/iter-0/parameters_justified.txt"

    res = _utils.read_parameters_txt(ptext)

    assert res["SENSNAME"] == "rms_seed"
    assert res["GLOBVAR"]["VOLON_PERMH_CHANNEL"] == 1100
    assert res["LOG10_MULTREGT"]["MULT_VALYSAR_THERYS"] == -3.2582


def test_get_runinfo_from_pwd(tmp_path):
    """Test that correct context is derived from the current working directory

    There are 4 known contexts, 2 are supported for now:

    1) ERT forward job -> return "ert_forward_job"
    2) RMS job, ERT run -> return "rms_job"
    3) ERT workflow job (not supported) -> return None
    4) RMS job, outside RMS (not supported) -> return None

    """

    # test case 1, context is forward job
    current = (
        tmp_path / "scratch" / "field" / "user" / "case" / "realization-10" / "iter-0"
    )
    current.mkdir(parents=True, exist_ok=True)
    res = _utils.get_runinfo_from_pwd(current)
    assert res["is_fmurun"] is True
    assert res["fmu_runcontext"] == "ert_forward_job"

    # test case 2, context is rms job run by ERT
    res = _utils.get_runinfo_from_pwd(current / "rms" / "model")
    assert res["is_fmurun"] is True
    assert res["fmu_runcontext"] == "rms_job"

    # test case 3, context is rms job not run by ERT
    current = tmp_path / "some" / "path" / "rms" / "model"
    res = _utils.get_runinfo_from_pwd(current)
    assert res["is_fmurun"] is False
    assert res["fmu_runcontext"] is None

    # test case 4, context is an ert workflow
    current = tmp_path / "some" / "path" / "ert" / "model"
    res = _utils.get_runinfo_from_pwd(current)
    assert res["is_fmurun"] is False
    assert res["fmu_runcontext"] is None
