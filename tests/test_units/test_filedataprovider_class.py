"""Test the _MetaData class from the _metadata.py module"""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import xtgeo
from fmu.datamodels.fmu_results import fields
from pytest import MonkeyPatch

from fmu.dataio import ExportData
from fmu.dataio._definitions import ExportFolder, ShareFolder
from fmu.dataio.providers._filedata import FileDataProvider, SharePathConstructor
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
    regsurf: xtgeo.RegularSurface,
    mock_exportdata: ExportData,
    name: str,
    tagname: str,
    parentname: str,
    time0: datetime | None,
    time1: datetime | None,
    expected: str,
) -> None:
    """Testing the private _get_filestem method."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    objdata.name = name
    # time0 is always the oldest
    objdata.time0 = time0
    objdata.time1 = time1

    mock_exportdata.tagname = tagname
    mock_exportdata.parent = parentname
    mock_exportdata.name = ""

    stem = SharePathConstructor(mock_exportdata._export_config, objdata)._get_filestem()
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
            "'time0' is missing while",
        ),
    ],
)
def test_get_filestem_shall_fail(
    regsurf: xtgeo.RegularSurface,
    mock_exportdata: ExportData,
    name: str,
    tagname: str,
    parentname: str,
    time0: datetime | None,
    time1: datetime,
    message: str,
) -> None:
    """Testing the private _get_filestem method when it shall fail."""
    mock_exportdata = deepcopy(mock_exportdata)
    mock_exportdata.tagname = tagname
    mock_exportdata.parent = parentname
    mock_exportdata.name = ""

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    objdata.name = name
    objdata.time0 = time0
    objdata.time1 = time1

    with pytest.raises(ValueError, match=message):
        _ = objdata.share_path


def test_get_share_folders(
    regsurf: xtgeo.RegularSurface, drogon_global_config: dict[str, Any]
) -> None:
    """Testing the get_share_folders method."""

    mock_exportdata = ExportData(
        config=drogon_global_config, name="some", content="depth"
    )

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    objdata.name = "some"

    fdata = FileDataProvider(mock_exportdata._export_config.runcontext, objdata)
    share_folders = objdata.share_path.parent
    assert isinstance(share_folders, Path)
    assert share_folders == Path(f"share/results/{ExportFolder.maps.value}")
    # check that the path present in the metadata matches the share folders

    fmeta = fdata.get_metadata()
    assert fmeta.absolute_path is not None
    assert str(fmeta.absolute_path.parent).endswith(
        f"share/results/{ExportFolder.maps.value}"
    )


def test_get_share_folders_with_subfolder(
    regsurf: xtgeo.RegularSurface, drogon_global_config: dict[str, Any]
) -> None:
    """Testing the private _get_path method, creating the path."""

    mock_exportdata = ExportData(
        config=drogon_global_config, name="some", subfolder="sub", content="depth"
    )

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    objdata.name = "some"

    assert objdata.share_path.parent == Path("share/results/maps/sub")
    fdata = FileDataProvider(mock_exportdata._export_config.runcontext, objdata)

    # check that the path present in the metadata matches the share folders
    fmeta = fdata.get_metadata()
    assert fmeta.absolute_path is not None
    assert str(fmeta.absolute_path.parent).endswith("share/results/maps/sub")


def test_filedata_provider(
    regsurf: xtgeo.RegularSurface,
    tmp_path: Path,
    drogon_global_config: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    """Testing the derive_filedata function."""

    monkeypatch.chdir(tmp_path)

    cfg = ExportData(
        config=drogon_global_config,
        name="",
        parent="parent",
        tagname="tag",
        forcefolder="efolder",
        content="depth",
    )
    objdata = objectdata_provider_factory(regsurf, cfg._export_config)
    objdata.name = "name"
    t1 = "19000101"
    t2 = "20240101"
    objdata.time0 = datetime.strptime(t1, "%Y%m%d")
    objdata.time1 = datetime.strptime(t2, "%Y%m%d")

    expected_path = Path(f"share/results/efolder/parent--name--tag--{t2}_{t1}.gri")

    assert objdata.share_path == expected_path

    fdata = FileDataProvider(cfg._export_config.runcontext, objdata)
    filemeta = fdata.get_metadata()

    assert isinstance(filemeta, fields.File)
    assert filemeta.relative_path == expected_path
    absdata = tmp_path / expected_path
    assert filemeta.absolute_path == absdata


def test_filedata_has_nonascii_letters(
    regsurf: xtgeo.RegularSurface,
    tmp_path: Path,
    drogon_global_config: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    """Testing the get_metadata function."""

    monkeypatch.chdir(tmp_path)
    mock_exportdata = ExportData(
        config=drogon_global_config, name="mynõme", content="depth"
    )

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    objdata.name = "anynõme"

    fdata = FileDataProvider(mock_exportdata._export_config.runcontext, objdata)
    with pytest.raises(ValueError, match="Path has non-ascii elements"):
        fdata.get_metadata()


def test_sharepath_get_share_root(
    regsurf: xtgeo.RegularSurface, drogon_global_config: dict[str, Any]
) -> None:
    """Test that the share root folder is correctly set."""

    # share/results
    exportdata = ExportData(
        config=drogon_global_config,
        content="depth",
        preprocessed=False,
        is_observation=False,
    )
    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)
    assert SharePathConstructor(
        exportdata._export_config, objdata
    )._get_share_root() == Path(ShareFolder.RESULTS.value)

    # share/preprosessed
    preprocessed_exportdata = ExportData(
        config=drogon_global_config,
        content="depth",
        preprocessed=True,
        is_observation=False,
    )
    objdata = objectdata_provider_factory(
        regsurf, preprocessed_exportdata._export_config
    )
    assert SharePathConstructor(
        preprocessed_exportdata._export_config, objdata
    )._get_share_root() == Path(ShareFolder.PREPROCESSED.value)

    # share/observations
    obs_exportdata = ExportData(
        config=drogon_global_config,
        content="depth",
        preprocessed=False,
        is_observation=True,
    )
    objdata = objectdata_provider_factory(regsurf, obs_exportdata._export_config)
    assert SharePathConstructor(
        obs_exportdata._export_config, objdata
    )._get_share_root() == Path(ShareFolder.OBSERVATIONS.value)

    # preprosessed should win over is_observation
    preprocessed_obs_exportdata = ExportData(
        config=drogon_global_config,
        content="depth",
        preprocessed=True,
        is_observation=True,
    )
    objdata = objectdata_provider_factory(
        regsurf, preprocessed_obs_exportdata._export_config
    )
    assert SharePathConstructor(
        preprocessed_obs_exportdata._export_config, objdata
    )._get_share_root() == Path(ShareFolder.PREPROCESSED.value)


def test_sharepath_with_date(
    drogon_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test that the share root folder is correctly set here using one date."""

    exportdata = ExportData(
        config=drogon_global_config,
        name="test",
        tagname="mytag",
        timedata=["20250512"],
        content="depth",
    )

    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)
    share_path = SharePathConstructor(exportdata._export_config, objdata)

    expected_filename = Path("test--mytag--20250512.gri")
    expected_path = Path(ShareFolder.RESULTS.value) / "maps" / expected_filename

    assert share_path.get_share_path() == expected_path
    assert objdata.share_path == expected_path


def test_sharepath_with_two_dates(
    drogon_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test that the share root folder is correctly set here using two dates."""

    exportdata = ExportData(
        config=drogon_global_config,
        name="test",
        tagname="mytag",
        timedata=["20250512", "20250511"],
        content="depth",
    )

    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)
    share_path = SharePathConstructor(exportdata._export_config, objdata)

    expected_filename = Path("test--mytag--20250512_20250511.gri")
    expected_path = Path(ShareFolder.RESULTS.value) / "maps" / expected_filename

    assert share_path.get_share_path() == expected_path
    assert objdata.share_path == expected_path


def test_sharepath_with_parent(
    drogon_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test that the share root folder is correctly set here
    using tagname and parent."""

    exportdata = ExportData(
        config=drogon_global_config,
        name="test",
        tagname="mytag",
        parent="myparent",
        content="depth",
    )

    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)
    share_path = SharePathConstructor(exportdata._export_config, objdata)

    expected_filename = Path("myparent--test--mytag.gri")
    expected_path = Path(ShareFolder.RESULTS.value) / "maps" / expected_filename

    assert share_path.get_share_path() == expected_path
    assert objdata.share_path == expected_path


def test_sharepath_name_from_objprovider(
    drogon_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test that the share root folder is correctly set using the
    name from the objdataprovider if not provided."""

    exportdata = ExportData(config=drogon_global_config, content="depth")

    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)
    share_path = SharePathConstructor(exportdata._export_config, objdata)

    expected_filename = Path(f"{objdata.name}.gri")
    expected_path = Path(ShareFolder.RESULTS.value) / "maps" / expected_filename

    assert share_path.get_share_path() == expected_path
    assert objdata.share_path == expected_path
