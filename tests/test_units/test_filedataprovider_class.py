"""Test the _MetaData class from the _metadata.py module"""
import os
from pathlib import Path

import pytest

from fmu.dataio._filedata_provider import _FileDataProvider
from fmu.dataio._objectdata_provider import _ObjectDataProvider


@pytest.mark.parametrize(
    "name, tagname, parentname, time0, time1, expected",
    [
        (
            "name",
            "tag",
            "parent",
            "2020-01-01",
            "2022-01-02",
            "parent--name--tag--20220102_20200101",
        ),
        (
            "name",
            "",
            "",
            "2020-01-01",
            "2022-01-02",
            "name--20220102_20200101",
        ),
        (
            "name",
            "",
            "",
            "2022-01-02",
            "",
            "name--20220102",
        ),
        (
            "name",
            "",
            "",
            "",
            "",
            "name",
        ),
        (
            "name",
            "",
            "",
            20210101,
            20220102,
            "name--20220102_20210101",
        ),
        (
            "name with spaces",
            "",
            "",
            "",
            "",
            "name_with_spaces",
        ),
        (
            "name with double  space",
            "",
            "",
            "",
            "",
            "name_with_double_space",
        ),
        (
            "name. some fm",
            "",
            "",
            "",
            "",
            "name_some_fm",
        ),
        (
            "name with many       ..   . spaces",
            "",
            "",
            "",
            "",
            "name_with_many_spaces",
        ),
    ],
)
def test_get_filestem(
    regsurf,
    edataobj1,
    name,
    tagname,
    parentname,
    time0,
    time1,
    expected,
):
    """Testing the private _get_filestem method."""
    objdata = _ObjectDataProvider(regsurf, edataobj1)
    objdata.name = name
    # time0 is always the oldest
    objdata.time0 = time0
    objdata.time1 = time1

    edataobj1.tagname = tagname
    edataobj1.parent = parentname
    edataobj1.name = ""

    fdata = _FileDataProvider(
        edataobj1,
        objdata,
    )

    stem = fdata._get_filestem()
    assert stem == expected


@pytest.mark.parametrize(
    "name, tagname, parentname, time0, time1, message",
    [
        (
            "",
            "tag",
            "parent",
            "2020-01-01",
            "2022-01-02",
            "'name' entry is missing",
        ),
        (
            "name",
            "tag",
            "parent",
            "",
            "2020-01-01",
            "'time1' is missing while",
        ),
    ],
)
def test_get_filestem_shall_fail(
    regsurf,
    edataobj1,
    name,
    tagname,
    parentname,
    time0,
    time1,
    message,
):
    """Testing the private _get_filestem method when it shall fail."""
    objdata = _ObjectDataProvider(regsurf, edataobj1)
    objdata.name = name
    objdata.time0 = time0
    objdata.time1 = time1

    edataobj1.tagname = tagname
    edataobj1.parent = parentname
    edataobj1.name = ""

    fdata = _FileDataProvider(edataobj1, objdata)

    with pytest.raises(ValueError) as msg:
        _ = fdata._get_filestem()
        assert message in str(msg)


def test_get_paths_path_exists_already(regsurf, edataobj1, tmp_path):
    """Testing the private _get_path method."""

    os.chdir(tmp_path)
    newpath = tmp_path / "share" / "results" / "efolder"
    newpath.mkdir(parents=True, exist_ok=True)

    edataobj1.name = "some"

    objdata = _ObjectDataProvider(regsurf, edataobj1)
    objdata.name = "some"
    objdata.efolder = "efolder"

    fdata = _FileDataProvider(edataobj1, objdata)

    path, linkpath = fdata._get_path()
    assert str(path) == "share/results/efolder"
    assert linkpath is None


def test_get_paths_not_exists_so_create(regsurf, edataobj1, tmp_path):
    """Testing the private _get_path method, creating the path."""

    os.chdir(tmp_path)

    objdata = _ObjectDataProvider(regsurf, edataobj1)
    objdata.name = "some"
    objdata.efolder = "efolder"
    cfg = edataobj1

    cfg.createfolder = True
    cfg._rootpath = Path(".")

    fdata = _FileDataProvider(cfg, objdata)

    path, _ = fdata._get_path()
    assert str(path) == "share/results/efolder"


def test_filedata_provider(regsurf, edataobj1, tmp_path):
    """Testing the derive_filedata function."""

    os.chdir(tmp_path)

    cfg = edataobj1
    cfg.createfolder = True
    cfg._rootpath = Path(".")
    cfg.name = ""

    objdata = _ObjectDataProvider(regsurf, edataobj1)
    objdata.name = "name"
    objdata.efolder = "efolder"
    objdata.extension = ".ext"
    objdata.time0 = "t1"
    objdata.time1 = "t2"

    fdata = _FileDataProvider(cfg, objdata)
    fdata.derive_filedata()

    print(fdata.relative_path)
    assert fdata.relative_path == "share/results/efolder/parent--name--tag--t2_t1.ext"
    absdata = str(tmp_path / "share/results/efolder/parent--name--tag--t2_t1.ext")
    assert fdata.absolute_path == absdata


def test_filedata_has_nonascii_letters(regsurf, edataobj1, tmp_path):
    """Testing the derive_filedata function."""

    os.chdir(tmp_path)

    cfg = edataobj1
    cfg.createfolder = True
    cfg._rootpath = Path(".")
    cfg.name = "mynõme"

    objdata = _ObjectDataProvider(regsurf, edataobj1)
    objdata.name = "anynõme"
    objdata.efolder = "efolder"
    objdata.extension = ".ext"
    objdata.time0 = "t1"
    objdata.time1 = "t2"

    fdata = _FileDataProvider(cfg, objdata)
    with pytest.raises(UnicodeEncodeError, match=r"codec can't encode character"):
        fdata.derive_filedata()
