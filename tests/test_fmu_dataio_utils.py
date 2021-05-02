"""Test the surface_io module."""
import pytest

import fmu.dataio._utils as _utils


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
            "unknown",
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
    """Testing veriy the path. TODO"""
    # path = _ut.verify_path(True, TMPDIR2, "file", ".myext")
    # assert str(path) == "TMP/some/folder/file.myext"
