"""Test the _MetaData class from the _metadata.py module"""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import xtgeo
from fmu.datamodels.fmu_results import fields
from fmu.datamodels.fmu_results.data import Time
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
            "20200101",
            "20220102",
            "parent--name--tag--20220102_20200101",
        ),
        (
            "name",
            "",
            "",
            "20200101",
            "20220102",
            "name--20220102_20200101",
        ),
        (
            "name",
            "",
            "",
            "20220102",
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
            "20210101",
            "20220102",
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
    time0: str | None,
    time1: str | None,
    expected: str,
) -> None:
    """Testing the private _get_filestem method."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    objdata._strat_element.name = name
    # time0 is always the oldest
    if time0 or time1:
        objdata._time = Time(
            t0=objdata._parse_timestamp(time0) if time0 else None,
            t1=objdata._parse_timestamp(time1) if time1 else None,
        )

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
            "20200101",
            "20200102",
            "'name' entry is missing",
        ),
        (
            "name",
            "tag",
            "parent",
            None,
            "20200101",
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
    time0: str | None,
    time1: str,
    message: str,
) -> None:
    """Testing the private _get_filestem method when it shall fail."""
    mock_exportdata = deepcopy(mock_exportdata)
    mock_exportdata.tagname = tagname
    mock_exportdata.parent = parentname
    mock_exportdata.name = name
    mock_exportdata.timedata = [time1]
    if time0:
        mock_exportdata.timedata.insert(0, time0)

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    objdata._strat_element.name = name
    objdata._time.t0 = objdata._parse_timestamp(time0) if time0 else None
    objdata._time.t1 = objdata._parse_timestamp(time1)

    with pytest.raises(ValueError, match=message):
        SharePathConstructor(mock_exportdata._export_config, objdata).get_share_path()


def test_get_share_folders(
    regsurf: xtgeo.RegularSurface, drogon_global_config: dict[str, Any]
) -> None:
    """Testing the get_share_folders method."""

    mock_exportdata = ExportData(
        config=drogon_global_config, name="some", content="depth"
    )

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    assert objdata.name == "some"

    share_path = SharePathConstructor(
        mock_exportdata._export_config, objdata
    ).get_share_path()

    fdata = FileDataProvider(
        mock_exportdata._export_config.runcontext, objdata, share_path
    )
    share_folders = share_path.parent
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
    objdata._strat_element.name = "some"

    share_path = SharePathConstructor(
        mock_exportdata._export_config, objdata
    ).get_share_path()
    assert share_path.parent == Path("share/results/maps/sub")

    fdata = FileDataProvider(
        mock_exportdata._export_config.runcontext, objdata, share_path
    )

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

    t0 = "19000101"
    t1 = "20240101"

    cfg = ExportData(
        config=drogon_global_config,
        name="",
        parent="parent",
        tagname="tag",
        forcefolder="efolder",
        content="depth",
        timedata=[t1, t0],
    )
    objdata = objectdata_provider_factory(regsurf, cfg._export_config)
    objdata._strat_element.name = "name"

    expected_path = Path(f"share/results/efolder/parent--name--tag--{t1}_{t0}.gri")

    share_path = SharePathConstructor(cfg._export_config, objdata).get_share_path()
    assert share_path == expected_path

    fdata = FileDataProvider(cfg._export_config.runcontext, objdata, share_path)
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
    objdata._strat_element.name = "anynõme"
    share_path = SharePathConstructor(
        mock_exportdata._export_config, objdata
    ).get_share_path()

    fdata = FileDataProvider(
        mock_exportdata._export_config.runcontext, objdata, share_path
    )
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
    share_path = SharePathConstructor(
        exportdata._export_config, objdata
    ).get_share_path()
    assert share_path == expected_path


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
    share_path = SharePathConstructor(
        exportdata._export_config, objdata
    ).get_share_path()
    assert share_path == expected_path


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
    share_path = SharePathConstructor(
        exportdata._export_config, objdata
    ).get_share_path()
    assert share_path == expected_path
