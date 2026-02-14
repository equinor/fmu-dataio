"""Test the ObjectDataProvider and its derived classes."""

from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import xtgeo
import yaml
from fmu.datamodels.fmu_results.specification import (
    FaultRoomSurfaceSpecification,
    TriangulatedSurfaceSpecification,
)
from pytest import MonkeyPatch

from fmu import dataio
from fmu.dataio._readers.faultroom import FaultRoomSurface
from fmu.dataio._readers.tsurf import TSurfData
from fmu.dataio.dataio import ExportData
from fmu.dataio.exceptions import ConfigurationError
from fmu.dataio.providers.objectdata._faultroom import FaultRoomSurfaceProvider
from fmu.dataio.providers.objectdata._provider import (
    objectdata_provider_factory,
)
from fmu.dataio.providers.objectdata._triangulated_surface import (
    TriangulatedSurfaceProvider,
)
from fmu.dataio.providers.objectdata._xtgeo import RegularSurfaceDataProvider


def test_resolve_stratigraphy_named_from_config(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """Name is resolved from stratigraphy config when present."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    res = objdata._resolve_stratigraphy()

    assert res.name == "Whatever Top"
    assert "TopWhatever" in res.alias
    assert res.stratigraphic is True


def test_resolve_stratigraphy_name_differs_from_input(
    regsurf: xtgeo.RegularSurface, drogon_exportdata: ExportData
) -> None:
    """Stratigraphy name differs from input name."""
    objdata = objectdata_provider_factory(regsurf, drogon_exportdata._export_config)
    res = objdata._resolve_stratigraphy()

    assert res.name == "VOLANTIS GP. Top"
    assert "TopVolantis" in res.alias
    assert res.stratigraphic is True


def test_resolve_stratigraphy_fallback_to_object_name(
    regsurf: xtgeo.RegularSurface,
    mock_global_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """When no explicit name, falls back to object name."""
    monkeypatch.chdir(tmp_path)
    regsurf.name = "MySurfaceName"

    exportdata = ExportData(config=mock_global_config, content="depth")
    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)

    assert objdata.name == "MySurfaceName"


def test_resolve_timedata_single_date(
    regsurf: xtgeo.RegularSurface,
    mock_global_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Single date is parsed correctly."""
    monkeypatch.chdir(tmp_path)

    exportdata = ExportData(
        config=mock_global_config,
        content="depth",
        name="test",
        timedata=["20230101"],
    )
    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)

    assert objdata.time0 == datetime(2023, 1, 1)
    assert objdata.time1 is None


def test_resolve_timedata_two_dates(
    regsurf: xtgeo.RegularSurface,
    mock_global_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Two dates are parsed and sorted correctly."""
    monkeypatch.chdir(tmp_path)

    exportdata = ExportData(
        config=mock_global_config,
        content="depth",
        name="test",
        timedata=["20240101", "20230101"],  # newer first
    )
    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)

    # Should be sorted so t0 is older
    assert objdata.time0 == datetime(2023, 1, 1)
    assert objdata.time1 == datetime(2024, 1, 1)


def test_resolve_timedata_with_labels(
    regsurf: xtgeo.RegularSurface,
    mock_global_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Timedata with labels is parsed correctly."""
    monkeypatch.chdir(tmp_path)

    exportdata = ExportData(
        config=mock_global_config,
        content="depth",
        name="test",
        timedata=[["20230101", "base"], ["20240101", "monitor"]],
    )
    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)

    assert objdata.time0 == datetime(2023, 1, 1)
    assert objdata.time1 == datetime(2024, 1, 1)
    assert objdata._time.t0.label == "base"
    assert objdata._time.t1.label == "monitor"


def test_resolve_timedata_none(
    regsurf: xtgeo.RegularSurface,
    mock_global_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """No timedata returns None."""
    monkeypatch.chdir(tmp_path)

    exportdata = ExportData(
        config=mock_global_config,
        content="depth",
        name="test",
    )
    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)

    assert objdata.time0 is None
    assert objdata.time1 is None
    assert objdata._time is None


def test_resolve_stratigraphy_not_in_config(
    regsurf: xtgeo.RegularSurface,
    mock_global_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """When name not in stratigraphy, returns simple element with input name."""
    monkeypatch.chdir(tmp_path)

    exportdata = ExportData(
        config=mock_global_config,
        content="depth",
        name="NotInStratigraphy",
    )
    objdata = objectdata_provider_factory(regsurf, exportdata._export_config)

    assert objdata.name == "NotInStratigraphy"
    assert objdata._strat_element.stratigraphic is False


def test_validate_forcefolder_absolute_raises(
    regsurf: xtgeo.RegularSurface,
    mock_global_config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Absolute path as forcefolder raises ValueError."""
    monkeypatch.chdir(tmp_path)

    exportdata = ExportData(
        config=mock_global_config,
        content="depth",
        name="test",
        forcefolder="/absolute/path",
    )

    with pytest.raises(ValueError, match="Can't use absolute path"):
        objectdata_provider_factory(regsurf, exportdata._export_config)


def test_factory_raises_on_unknown_type(mock_exportdata: ExportData) -> None:
    """Factory raises NotImplementedError for unknown types."""
    with pytest.raises(NotImplementedError, match="not currently supported"):
        objectdata_provider_factory(object(), mock_exportdata._export_config)


def test_factory_returns_correct_provider_regularsurface(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """Factory returns RegularSurfaceDataProvider for RegularSurface."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    assert isinstance(objdata, RegularSurfaceDataProvider)


def test_factory_returns_correct_provider_faultroom(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """Factory returns FaultRoomSurfaceProvider for FaultRoomSurface."""
    objdata = objectdata_provider_factory(
        faultroom_object, drogon_exportdata._export_config
    )
    assert isinstance(objdata, FaultRoomSurfaceProvider)


def test_factory_returns_correct_provider_tsurf(
    tsurf: TSurfData, drogon_exportdata: ExportData
) -> None:
    """Factory returns TriangulatedSurfaceProvider for TSurfData."""
    objdata = objectdata_provider_factory(tsurf, drogon_exportdata._export_config)
    assert isinstance(objdata, TriangulatedSurfaceProvider)


def test_regularsurface_extension(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """RegularSurface has correct extension."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    assert objdata.extension == ".gri"


def test_regularsurface_classname(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """RegularSurface has correct classname."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    assert objdata.classname.value == "surface"


def test_regularsurface_spec_bbox(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """RegularSurface spec and bbox are derived correctly."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    specs = objdata.get_spec()
    bbox = objdata.get_bbox()

    assert specs.ncol == regsurf.ncol
    assert bbox.xmin == 0.0
    assert bbox.zmin == 1234.0


def test_regularsurface_metadata(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """RegularSurface metadata is derived correctly."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    metadata = objdata.get_metadata()

    assert metadata.root.content == "depth"
    assert metadata.root.alias


def test_faultroom_properties(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface has correct properties."""
    objdata = objectdata_provider_factory(
        faultroom_object, drogon_exportdata._export_config
    )

    assert objdata.extension == ".json"
    assert objdata.layout == "triangulated"


def test_faultroom_bbox(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface bbox is derived correctly."""
    objdata = objectdata_provider_factory(
        faultroom_object, drogon_exportdata._export_config
    )
    bbox = objdata.get_bbox()

    assert bbox.xmin == 1.1
    assert bbox.zmax == 2.3


def test_faultroom_spec_juxtaposition(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface juxtaposition names are resolved from stratigraphy."""
    objdata = objectdata_provider_factory(
        faultroom_object, drogon_exportdata._export_config
    )
    spec = objdata.get_spec()

    assert isinstance(spec, FaultRoomSurfaceSpecification)
    assert spec.juxtaposition_fw == ["Valysar Fm.", "Therys Fm.", "Volon Fm."]
    assert spec.juxtaposition_hw == ["Valysar Fm.", "Therys Fm.", "Volon Fm."]


def test_faultroom_export_to_file(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface exports to JSON format."""
    objdata = objectdata_provider_factory(
        faultroom_object, drogon_exportdata._export_config
    )

    buffer = BytesIO()
    objdata.export_to_file(buffer)
    buffer.seek(0)

    expected = """{\n    "metadata": {\n        "horizons":"""
    assert buffer.read(len(expected)).decode("utf-8") == expected


def test_tsurf_properties(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf has correct properties."""
    objdata = objectdata_provider_factory(tsurf, drogon_exportdata._export_config)

    assert objdata.classname.value == "surface"
    assert objdata.efolder == "maps"
    assert objdata.extension == ".ts"
    assert objdata.fmt == "tsurf"
    assert objdata.layout == "triangulated"


def test_tsurf_bbox(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf bbox is derived correctly."""
    objdata = objectdata_provider_factory(tsurf, drogon_exportdata._export_config)
    bbox = objdata.get_bbox()

    assert bbox.xmin == 0.1
    assert bbox.xmax == 3.1
    assert bbox.ymin == 0.2
    assert bbox.ymax == 3.2
    assert bbox.zmin == 0.3
    assert bbox.zmax == 3.3


def test_tsurf_spec(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf spec is derived correctly."""
    objdata = objectdata_provider_factory(tsurf, drogon_exportdata._export_config)
    spec = objdata.get_spec()

    assert isinstance(spec, TriangulatedSurfaceSpecification)
    assert spec.num_vertices == 4
    assert spec.num_triangles == 2


def test_tsurf_export_to_file(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf exports to correct format."""
    objdata = objectdata_provider_factory(tsurf, drogon_exportdata._export_config)

    buffer = BytesIO()
    objdata.export_to_file(buffer)
    buffer.seek(0)

    assert buffer.read(14).decode("utf-8") == "GOCAD TSurf 1\n"


def test_table_invalid_format_raises(
    dataframe: pd.DataFrame, mock_exportdata: ExportData
) -> None:
    """Invalid table format raises ConfigurationError."""
    mock_exportdata.table_fformat = "roff"

    with pytest.raises(ConfigurationError):
        _ = objectdata_provider_factory(
            dataframe, mock_exportdata._export_config
        ).extension

    mock_exportdata.table_fformat = "csv"  # reset


def test_compute_md5_and_size(
    gridproperty: xtgeo.GridProperty, mock_exportdata: ExportData
) -> None:
    """MD5 and size computation matches metadata."""
    objdata = objectdata_provider_factory(gridproperty, mock_exportdata._export_config)

    metadata = mock_exportdata.generate_metadata(gridproperty)
    checksum, size = objdata.compute_md5_and_size()

    assert metadata["file"]["checksum_md5"] == checksum
    assert metadata["file"]["size_bytes"] == size


def test_preprocessed_observation_workflow(
    fmurun_prehook: Path,
    rmssetup: Path,
    rmsglobalconfig: dict[str, Any],
    regsurf: xtgeo.RegularSurface,
    monkeypatch: MonkeyPatch,
    remove_ert_env: Callable[[], None],
    set_ert_env_prehook: Callable[[], None],
) -> None:
    """Test generating pre-realization surfaces that comes to share/preprocessed.

    Later, a fmu run will update this (merge metadata)
    """

    @pytest.mark.usefixtures("inside_rms_interactive")
    def _export_data_from_rms(
        rmssetup: Path,
        rmsglobalconfig: dict[str, Any],
        regsurf: xtgeo.RegularSurface,
        monkeypatch: MonkeyPatch,
    ) -> tuple[ExportData, str]:
        """Run an export of a preprocessed surface inside RMS."""

        monkeypatch.chdir(rmssetup)
        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            preprocessed=True,
            name="TopVolantis",
            content="depth",
            is_observation=True,
            timedata=[["20240802", "moni"], ["20200909", "base"]],
        )
        return edata, edata.export(regsurf)

    def _run_case_fmu(
        fmurun_prehook: Path, surfacepath: Path, monkeypatch: MonkeyPatch
    ) -> dict[str, Any]:
        """Run FMU workflow, using the preprocessed data as case data.

        When re-using metadata, the input object to dataio shall not be a XTGeo or
        Pandas or ... instance, but just a file path (either as string or a pathlib.Path
        object). This is because we want to avoid time and resources spent on double
        reading e.g. a seismic cube, but rather trigger a file copy action instead.

        But it requires that valid metadata for that file is found. The rule for
        merging is currently defaulted to "preprocessed".
        """
        monkeypatch.chdir(fmurun_prehook)

        casepath = fmurun_prehook
        edata = dataio.ExportPreprocessedData(is_observation=True, casepath=casepath)
        return edata.generate_metadata(surfacepath)

    # run two stage process
    remove_ert_env()
    edata, mysurf = _export_data_from_rms(
        rmssetup, rmsglobalconfig, regsurf, monkeypatch
    )
    set_ert_env_prehook()
    case_meta = _run_case_fmu(fmurun_prehook, mysurf, monkeypatch)

    out = Path(mysurf)
    with open(out.parent / f".{out.name}.yml", encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    assert metadata["data"] == case_meta["data"]
