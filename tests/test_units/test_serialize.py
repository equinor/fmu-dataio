"""Tests for the _export.serialize module."""

from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pytest
import xtgeo

from fmu.dataio._export.serialize import compute_md5_and_size, export_object
from fmu.dataio._metadata import ObjectData, create_object_data
from fmu.dataio._readers.tsurf import TSurfData
from fmu.dataio._utils import md5sum
from fmu.dataio.dataio import ExportData
from fmu.dataio.types import ExportableData


@pytest.fixture
def make_objdata(
    mock_exportdata: ExportData,
) -> Callable[[ExportableData], ObjectData]:
    """Helper to create ObjectData from a raw object."""

    def _make_objdata(obj: ExportableData) -> ObjectData:
        return create_object_data(obj, mock_exportdata._export_config)

    return _make_objdata


@pytest.mark.parametrize(
    "obj_fixture, expected_prefix",
    [
        ("regsurf", b"\x00"),  # irap_binary starts with null byte
        ("grid", b"roff"),  # roff format tag
        ("gridproperty", b"roff"),
        ("dataframe", b"COL"),  # csv header starts with first column name
        ("arrowtable", b"PAR1"),  # parquet magic bytes
    ],
)
def test_export_object_produces_bytes(
    obj_fixture: str,
    expected_prefix: bytes,
    make_objdata: Callable[[ExportableData], ObjectData],
    request: pytest.FixtureRequest,
) -> None:
    """export_object writes non-empty output for each supported type.

    Cubes are not present here as they cannot write to memory streams."""
    obj = request.getfixturevalue(obj_fixture)
    objdata = make_objdata(obj)

    buffer = BytesIO()
    export_object(objdata, buffer)

    assert buffer.tell() > 0
    if expected_prefix:
        buffer.seek(0)
        assert buffer.read(len(expected_prefix)) == expected_prefix


def test_export_cube_to_file(
    tmp_path: Path,
    cube: xtgeo.Cube,
    make_objdata: Callable[[ExportableData], ObjectData],
) -> None:
    """Cube exports to segy (requires file path, not buffer)."""
    objdata = make_objdata(cube)
    outfile = tmp_path / "test.segy"
    export_object(objdata, outfile)
    assert outfile.stat().st_size > 0


def test_export_dict(make_objdata: Callable[[ExportableData], ObjectData]) -> None:
    """Dictionaries serialize to JSON."""
    objdata = make_objdata({"key": "value", "num": 42})

    buffer = BytesIO()
    export_object(objdata, buffer)
    buffer.seek(0)

    assert b'"key"' in buffer.read()


def test_export_tsurf(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf serializes to GOCAD format."""
    objdata = create_object_data(tsurf, drogon_exportdata._export_config)

    buffer = BytesIO()
    export_object(objdata, buffer)
    buffer.seek(0)

    assert buffer.read(14) == b"GOCAD TSurf 1\n"


def test_export_unsupported_type(
    make_objdata: Callable[[ExportableData], ObjectData],
) -> None:
    """Unsupported object types raise NotImplementedError."""

    class FakeData:
        name = "fake"

    objdata = make_objdata({"x": 1})  # valid objdata to get the structure
    objdata.obj = FakeData()  # swap in unsupported type

    with pytest.raises(NotImplementedError, match="FakeData"):
        export_object(objdata, BytesIO())


def test_compute_md5_deterministic(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """Same object produces the same md5 and size on repeated calls."""
    objdata = create_object_data(regsurf, mock_exportdata._export_config)

    result1 = compute_md5_and_size(objdata)
    result2 = compute_md5_and_size(objdata)

    assert result1 == result2
    assert len(result1[0]) == 32  # md5 hex digest length
    assert result1[1] > 0


def test_compute_md5_matches_export(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """md5 from compute_md5_and_size matches direct buffer export."""

    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    checksum, size = compute_md5_and_size(objdata)

    buffer = BytesIO()
    export_object(objdata, buffer)

    assert md5sum(buffer) == checksum
    assert buffer.getbuffer().nbytes == size
