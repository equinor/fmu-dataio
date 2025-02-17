"""Test the _MetaData class from the _metadata.py module"""

import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from fmu.dataio import ExportData
from fmu.dataio._definitions import ExportFolder
from fmu.dataio._models.fmu_results import fields
from fmu.dataio.providers._filedata import FileDataProvider
from fmu.dataio.providers.objectdata._provider import objectdata_provider_factory


@pytest.mark.parametrize(
    "name, tagname, parentname, time0, time1, expected",
    [
        (
            "name",
            "tag",
            "parent",
            datetime.strptime("2020-01-01", "%Y-%m-%d"),
            datetime.strptime("2022-01-02", "%Y-%m-%d"),
            "parent--name--tag--20220102_20200101",
        ),
        (
            "name",
            "",
            "",
            datetime.strptime("2020-01-01", "%Y-%m-%d"),
            datetime.strptime("2022-01-02", "%Y-%m-%d"),
            "name--20220102_20200101",
        ),
        (
            "name",
            "",
            "",
            datetime.strptime("2022-01-02", "%Y-%m-%d"),
            None,
            "name--20220102",
        ),
        (
            "name",
            "",
            "",
            None,
            None,
            "name",
        ),
        (
            "name",
            "",
            "",
            datetime.strptime("2021-01-01", "%Y-%m-%d"),
            datetime.strptime("2022-01-02", "%Y-%m-%d"),
            "name--20220102_20210101",
        ),
        (
            "name with spaces",
            "",
            "",
            None,
            None,
            "name_with_spaces",
        ),
        (
            "name with double  space",
            "",
            "",
            None,
            None,
            "name_with_double_space",
        ),
        (
            "name. some fm",
            "",
            "",
            None,
            None,
            "name_some_fm",
        ),
        (
            "name with many       ..   . spaces",
            "",
            "",
            None,
            None,
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
    objdata = objectdata_provider_factory(regsurf, edataobj1)
    objdata.name = name
    # time0 is always the oldest
    objdata.time0 = time0
    objdata.time1 = time1

    edataobj1.tagname = tagname
    edataobj1.parent = parentname
    edataobj1.name = ""

    fdata = FileDataProvider(edataobj1, objdata, regsurf)

    stem = fdata._get_filestem()
    assert stem == expected


@pytest.mark.parametrize(
    "name, tagname, parentname, time0, time1, message",
    [
        (
            "",
            "tag",
            "parent",
            datetime.strptime("2020-01-01", "%Y-%m-%d"),
            datetime.strptime("2022-01-02", "%Y-%m-%d"),
            "'name' entry is missing",
        ),
        (
            "name",
            "tag",
            "parent",
            None,
            datetime.strptime("2020-01-01", "%Y-%m-%d"),
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
    objdata = objectdata_provider_factory(regsurf, edataobj1)
    objdata.name = name
    objdata.time0 = time0
    objdata.time1 = time1

    edataobj1 = deepcopy(edataobj1)
    edataobj1.tagname = tagname
    edataobj1.parent = parentname
    edataobj1.name = ""

    fdata = FileDataProvider(edataobj1, objdata, regsurf)

    with pytest.raises(ValueError) as msg:
        _ = fdata._get_filestem()
        assert message in str(msg)


def test_get_share_folders(regsurf, globalconfig2):
    """Testing the get_share_folders method."""

    edataobj1 = ExportData(config=globalconfig2, name="some", content="depth")

    objdata = objectdata_provider_factory(regsurf, edataobj1)
    objdata.name = "some"

    fdata = FileDataProvider(edataobj1, objdata, regsurf)
    share_folders = fdata._get_share_folders()
    assert isinstance(share_folders, Path)
    assert share_folders == Path(f"share/results/{ExportFolder.maps.value}")
    # check that the path present in the metadata matches the share folders

    fmeta = fdata.get_metadata()
    assert str(fmeta.absolute_path.parent).endswith(
        f"share/results/{ExportFolder.maps.value}"
    )


def test_get_share_folders_with_subfolder(regsurf, globalconfig2):
    """Testing the private _get_path method, creating the path."""

    edataobj1 = ExportData(
        config=globalconfig2, name="some", subfolder="sub", content="depth"
    )

    objdata = objectdata_provider_factory(regsurf, edataobj1)
    objdata.name = "some"

    fdata = FileDataProvider(edataobj1, objdata, regsurf)
    share_folders = fdata._get_share_folders()
    assert share_folders == Path("share/results/maps/sub")

    # check that the path present in the metadata matches the share folders
    fmeta = fdata.get_metadata()
    assert str(fmeta.absolute_path.parent).endswith("share/results/maps/sub")


@pytest.mark.skip_inside_rmsvenv
def test_filedata_provider(regsurf, tmp_path, globalconfig2):
    """Testing the derive_filedata function."""

    # TODO: Refactor tests and move away from outside/inside rms pattern

    os.chdir(tmp_path)

    cfg = ExportData(
        config=globalconfig2,
        name="",
        parent="parent",
        tagname="tag",
        forcefolder="efolder",
        content="depth",
    )
    objdata = objectdata_provider_factory(regsurf, cfg)
    objdata.name = "name"
    t1 = "19000101"
    t2 = "20240101"
    objdata.time0 = datetime.strptime(t1, "%Y%m%d")
    objdata.time1 = datetime.strptime(t2, "%Y%m%d")

    fdata = FileDataProvider(cfg, objdata, regsurf)
    filemeta = fdata.get_metadata()

    assert isinstance(filemeta, fields.File)
    assert (
        str(filemeta.relative_path)
        == f"share/results/efolder/parent--name--tag--{t2}_{t1}.gri"
    )
    absdata = tmp_path / f"share/results/efolder/parent--name--tag--{t2}_{t1}.gri"
    assert filemeta.absolute_path == absdata


def test_filedata_has_nonascii_letters(regsurf, tmp_path, globalconfig2):
    """Testing the get_metadata function."""

    os.chdir(tmp_path)
    edataobj1 = ExportData(config=globalconfig2, name="mynõme", content="depth")

    objdata = objectdata_provider_factory(regsurf, edataobj1)
    objdata.name = "anynõme"

    fdata = FileDataProvider(edataobj1, objdata, regsurf)
    with pytest.raises(ValueError, match="Path has non-ascii elements"):
        fdata.get_metadata()
