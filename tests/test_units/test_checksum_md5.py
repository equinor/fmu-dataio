from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import xtgeo
from pytest import MonkeyPatch

from fmu.dataio._readers import faultroom
from fmu.dataio._utils import md5sum
from fmu.dataio.dataio import ExportData, read_metadata


def test_checksum_md5_for_regsurf(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig1: dict[str, Any],
    regsurf: xtgeo.RegularSurface,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for an xtgeo.RegularSurface
    """
    monkeypatch.chdir(tmp_path)

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(regsurf)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_gridproperty(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig1: dict[str, Any],
    gridproperty: xtgeo.GridProperty,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for an xtgeo.GridProperty
    """
    monkeypatch.chdir(tmp_path)

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(gridproperty)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_grid(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig1: dict[str, Any],
    grid: xtgeo.Grid,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for an xtgeo.Grid
    """
    monkeypatch.chdir(tmp_path)

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(grid)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_points(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig1: dict[str, Any],
    points: xtgeo.Points,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for an xtgeo.Points
    """
    monkeypatch.chdir(tmp_path)

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(points)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_polygons(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig1: dict[str, Any],
    polygons: xtgeo.Polygons,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for an xtgeo.Polygons
    """
    monkeypatch.chdir(tmp_path)

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(polygons)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_cube(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig1: dict[str, Any],
    cube: xtgeo.Cube,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for an xtgeo.Cube
    """
    monkeypatch.chdir(tmp_path)

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(cube)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_dataframe(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig1: dict[str, Any],
    dataframe: pd.DataFrame,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for an pandas.DataFrame
    """
    monkeypatch.chdir(tmp_path)

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(dataframe)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_arrowtable(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig1: dict[str, Any],
    arrowtable: pa.Table,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for an pyarrow.Table
    """
    monkeypatch.chdir(tmp_path)

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(arrowtable)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_dictionary(
    monkeypatch: MonkeyPatch, tmp_path: Path, globalconfig1: dict[str, Any]
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for a dictionary
    """
    monkeypatch.chdir(tmp_path)

    mydict = {"test": 3, "test2": "string", "test3": {"test4": 100.89}}

    export_path = Path(
        ExportData(
            config=globalconfig1,
            content="depth",
            name="myname",
        ).export(mydict)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)


def test_checksum_md5_for_faultroom(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    globalconfig2: dict[str, Any],
    rootpath: Path,
) -> None:
    """
    Test that the MD5 hash in the metadata is equal to one computed for
    the exported file for a FaultRoomSurface
    """
    monkeypatch.chdir(tmp_path)

    faultroom_files = (rootpath / "tests/data/drogon/rms/output/faultroom").glob(
        "*.json"
    )
    fault_room_surface = faultroom.read_faultroom_file(next(faultroom_files))

    export_path = Path(
        ExportData(
            config=globalconfig2,
            content="depth",
            name="myname",
        ).export(fault_room_surface)
    )

    meta = read_metadata(export_path)
    assert meta["file"]["checksum_md5"] == md5sum(export_path)
