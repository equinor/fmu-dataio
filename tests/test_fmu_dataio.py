import pathlib
from collections import OrderedDict
import pytest

import xtgeo

import fmu.dataio
import fmu.dataio._surface_io as _sio
import fmu.dataio._utils as _ut

CFG = OrderedDict()
CFG["template"] = {"name": "Test", "revision": "AUTO"}
CFG["masterdata"] = {
    "smda": {
        "country": [
            {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
        ],
        "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
    }
}

# prefer this to pytest tmp_path / tmpdir fixtures to have control of output path
TMPDIR = pathlib.Path("TMP")
TMPDIR.mkdir(parents=True, exist_ok=True)
TMPDIR2 = TMPDIR / "some" / "folder"
TMPDIR2.mkdir(parents=True, exist_ok=True)


def test_instantate_class():
    """Test function _get_meta_master."""
    case = fmu.dataio.ExportData(config=CFG)
    assert isinstance(case._config, dict)


def test_surface_io():
    """Test surface io, fmu=99 uses tmp_path."""
    # dataio = fmu.dataio.ExportData(config=CFG)
    # regsurf = xtgeo.RegularSurface()

    pass


@pytest.mark.parametrize(
    "name, hash_, descr, t1, t2, loc, expectedstem, expectedpath",
    [
        (
            "some",
            "1234",
            "case1",
            None,
            None,
            "surface",
            "some--case1--1234",
            "../../share/results/maps",
        ),
        (
            "some",
            "9876",
            "case2",
            None,
            None,
            "grid",
            "some--case2--9876",
            "../../share/results/grids",
        ),
        (
            "some",
            "9876",
            None,
            None,
            None,
            "wrong",
            "some--9876",
            "../../share/results/unknown",
        ),
        (
            "some",
            "9876",
            None,
            20200101,
            None,
            "grid",
            "some--20200101--9876",
            "../../share/results/grids",
        ),
        (
            "some",
            "9876",
            "case8",
            20200101,
            20400909,
            "grid",
            "some--case8--20400909_20200101--9876",
            "../../share/results/grids",
        ),
    ],
)
def test_utility_functions(name, hash_, descr, t1, t2, loc, expectedstem, expectedpath):
    """Testing simple function in _utils.py."""

    stem, dest = _ut.construct_filename(
        name, hash_, descr=descr, loc=loc, t1=t1, t2=t2, filedest=TMPDIR2
    )

    assert stem == expectedstem
    assert dest == "TMP/some/folder/" + expectedpath


def test_verify_path():
    """Return path."""
    path = _ut.verify_path(True, TMPDIR2, "file", ".myext")

    assert str(path) == "TMP/some/folder/file.myext"
