"""Test the ObjectData and its derived classes."""

from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
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
from fmu.dataio import ExportData
from fmu.dataio._export.serialize import compute_md5_and_size, export_object
from fmu.dataio._metadata import create_object_data
from fmu.dataio._metadata._object._faultroom import FaultRoomSurfaceData
from fmu.dataio._metadata._object._triangulated_surface import (
    TriangulatedSurfaceData,
)
from fmu.dataio._metadata._object._utils import get_value_statistics
from fmu.dataio._metadata._object._xtgeo import RegularSurfaceData
from fmu.dataio._readers.faultroom import FaultRoomSurface
from fmu.dataio._readers.tsurf import TSurfData
from fmu.dataio.exceptions import ConfigurationError


def test_resolve_stratigraphy_named_from_config(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """Name is resolved from stratigraphy config when present."""
    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    res = objdata._resolve_stratigraphy()

    assert res.name == "Whatever Top"
    assert "TopWhatever" in res.alias
    assert res.stratigraphic is True


def test_resolve_stratigraphy_name_differs_from_input(
    regsurf: xtgeo.RegularSurface, drogon_exportdata: ExportData
) -> None:
    """Stratigraphy name differs from input name."""
    objdata = create_object_data(regsurf, drogon_exportdata._export_config)
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
    objdata = create_object_data(regsurf, exportdata._export_config)

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
    objdata = create_object_data(regsurf, exportdata._export_config)

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
    objdata = create_object_data(regsurf, exportdata._export_config)

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
    objdata = create_object_data(regsurf, exportdata._export_config)

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
    objdata = create_object_data(regsurf, exportdata._export_config)

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
    objdata = create_object_data(regsurf, exportdata._export_config)

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
        create_object_data(regsurf, exportdata._export_config)


def test_factory_raises_on_unknown_type(mock_exportdata: ExportData) -> None:
    """Factory raises NotImplementedError for unknown types."""
    with pytest.raises(NotImplementedError, match="not currently supported"):
        create_object_data(object(), mock_exportdata._export_config)


def test_factory_returns_correct_provider_regularsurface(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """Factory returns RegularSurfaceData for RegularSurface."""
    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    assert isinstance(objdata, RegularSurfaceData)


def test_factory_returns_correct_provider_faultroom(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """Factory returns FaultRoomSurfaceData for FaultRoomSurface."""
    objdata = create_object_data(faultroom_object, drogon_exportdata._export_config)
    assert isinstance(objdata, FaultRoomSurfaceData)


def test_factory_returns_correct_provider_tsurf(
    tsurf: TSurfData, drogon_exportdata: ExportData
) -> None:
    """Factory returns TriangulatedSurfaceData for TSurfData."""
    objdata = create_object_data(tsurf, drogon_exportdata._export_config)
    assert isinstance(objdata, TriangulatedSurfaceData)


def test_regularsurface_extension(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """RegularSurface has correct extension."""
    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    assert objdata.extension == ".gri"


def test_regularsurface_classname(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """RegularSurface has correct classname."""
    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    assert objdata.classname.value == "surface"


def test_regularsurface_spec_bbox(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """RegularSurface spec and bbox are derived correctly."""
    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    specs = objdata.get_spec()
    bbox = objdata.get_bbox()

    assert specs.ncol == regsurf.ncol
    assert bbox.xmin == 0.0
    assert bbox.zmin == 1234.0


def test_regularsurface_get_bbox_ignores_nan(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """get_bbox ignores NaN values in surface values."""

    regsurf.values[0, :] = np.nan

    objdata = create_object_data(regsurf, mock_exportdata._export_config)

    bbox = objdata.get_bbox()

    assert bbox is not None

    assert hasattr(bbox, "zmin")
    assert hasattr(bbox, "zmax")

    expected_zmin = np.nanmin(regsurf.values)
    expected_zmax = np.nanmax(regsurf.values)

    assert not np.isnan(expected_zmin)
    assert not np.isnan(expected_zmax)

    assert bbox.zmin == expected_zmin
    assert bbox.zmax == expected_zmax

    assert bbox.xmin == regsurf.xmin
    assert bbox.xmax == regsurf.xmax
    assert bbox.ymin == regsurf.ymin
    assert bbox.ymax == regsurf.ymax


def test_gridproperty_spec_value_statistics(
    mock_exportdata: ExportData,
) -> None:
    """GridProperty spec value_statistics are derived correctly."""
    gridprop = xtgeo.GridProperty(ncol=3, nrow=3, nlay=3, values=5)

    # set first and last layer to different values
    gridprop.values[:, :, 0] = 0
    gridprop.values[:, :, 2] = 10

    objdata = create_object_data(gridprop, mock_exportdata._export_config)
    specs = objdata.get_spec()

    stats = get_value_statistics(gridprop.values)
    assert specs.value_statistics == stats

    assert specs.value_statistics.min == 0
    assert specs.value_statistics.max == 10
    assert specs.value_statistics.mean == 5
    np.testing.assert_almost_equal(specs.value_statistics.std, 4.082, decimal=3)


def test_regularsurface_spec_value_statistics(mock_exportdata: ExportData) -> None:
    """RegularSurface spec value_statistics are derived correctly."""
    regsurf = xtgeo.RegularSurface(ncol=3, nrow=3, xinc=1, yinc=1, values=5)

    # set first and last column to different values
    regsurf.values[0, :] = 0
    regsurf.values[2, :] = 10

    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    specs = objdata.get_spec()

    stats = get_value_statistics(regsurf.values)
    assert specs.value_statistics == stats

    assert specs.value_statistics.min == 0
    assert specs.value_statistics.max == 10
    assert specs.value_statistics.mean == 5
    np.testing.assert_almost_equal(specs.value_statistics.std, 4.082, decimal=3)


def test_regularsurface_spec_value_statistics_with_nan(
    mock_exportdata: ExportData,
) -> None:
    """
    RegularSurface spec value_statistics are derived correctly for a
    surface with nan values.
    """
    regsurf = xtgeo.RegularSurface(ncol=3, nrow=3, xinc=1, yinc=1, values=5)
    regsurf.values[0, :] = np.nan

    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    specs = objdata.get_spec()

    assert specs.value_statistics.min == 5
    assert specs.value_statistics.max == 5
    assert specs.value_statistics.mean == 5
    assert specs.value_statistics.std == 0


def test_regularsurface_spec_value_statistics_only_nan(
    mock_exportdata: ExportData,
) -> None:
    """
    RegularSurface spec value_statistics are derived correctly for a
    surface with only nan values.
    """
    regsurf = xtgeo.RegularSurface(ncol=3, nrow=3, xinc=1, yinc=1, values=5)
    regsurf.values[:] = np.nan

    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    specs = objdata.get_spec()

    assert specs.value_statistics is None


def test_regularsurface_metadata(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    """RegularSurface metadata is derived correctly."""
    objdata = create_object_data(regsurf, mock_exportdata._export_config)
    metadata = objdata.get_metadata()

    assert metadata.root.content == "depth"
    assert metadata.root.alias


def test_faultroom_properties(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface has correct properties."""
    objdata = create_object_data(faultroom_object, drogon_exportdata._export_config)

    assert objdata.extension == ".json"
    assert objdata.layout == "triangulated"


def test_faultroom_bbox(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface bbox is derived correctly."""
    objdata = create_object_data(faultroom_object, drogon_exportdata._export_config)
    bbox = objdata.get_bbox()

    assert bbox.xmin == 1.1
    assert bbox.zmax == 2.3


def test_faultroom_fault_groups(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface fault groups are derived correctly."""

    # Modify the faultroom object to have faults in group format
    faultroom_object.storage["metadata"]["faults"] = {
        "best_faults": ["F1", "F2", "F3"],
        "even_better_faults": ["F4", "F5"],
        "absolutely_best_faults": ["F6"],
    }
    faultroom_object._set_faults()

    objdata = create_object_data(faultroom_object, drogon_exportdata._export_config)
    spec = objdata.get_spec()

    assert spec.faults == ["F1", "F2", "F3", "F4", "F5", "F6"]


def test_faultroom_spec_juxtaposition(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface juxtaposition names are resolved from stratigraphy."""
    objdata = create_object_data(faultroom_object, drogon_exportdata._export_config)
    spec = objdata.get_spec()

    assert isinstance(spec, FaultRoomSurfaceSpecification)
    assert spec.juxtaposition_fw == ["Valysar Fm.", "Therys Fm.", "Volon Fm."]
    assert spec.juxtaposition_hw == ["Valysar Fm.", "Therys Fm.", "Volon Fm."]


def test_faultroom_export_to_file(
    faultroom_object: FaultRoomSurface, drogon_exportdata: ExportData
) -> None:
    """FaultRoomSurface exports to JSON format."""
    objdata = create_object_data(faultroom_object, drogon_exportdata._export_config)

    buffer = BytesIO()
    export_object(objdata, buffer)
    buffer.seek(0)

    expected = """{\n    "metadata": {\n        "horizons":"""
    assert buffer.read(len(expected)).decode("utf-8") == expected


def test_tsurf_properties(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf has correct properties."""
    objdata = create_object_data(tsurf, drogon_exportdata._export_config)

    assert objdata.classname.value == "surface"
    assert objdata.efolder == "maps"
    assert objdata.extension == ".ts"
    assert objdata.fmt == "tsurf"
    assert objdata.layout == "triangulated"


def test_tsurf_bbox(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf bbox is derived correctly."""
    objdata = create_object_data(tsurf, drogon_exportdata._export_config)
    bbox = objdata.get_bbox()

    assert bbox.xmin == 0.1
    assert bbox.xmax == 3.1
    assert bbox.ymin == 0.2
    assert bbox.ymax == 3.2
    assert bbox.zmin == 0.3
    assert bbox.zmax == 3.3


def test_tsurf_spec(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf spec is derived correctly."""
    objdata = create_object_data(tsurf, drogon_exportdata._export_config)
    spec = objdata.get_spec()

    assert isinstance(spec, TriangulatedSurfaceSpecification)
    assert spec.num_vertices == 4
    assert spec.num_triangles == 2


def test_tsurf_export_to_file(tsurf: TSurfData, drogon_exportdata: ExportData) -> None:
    """TSurf exports to correct format."""
    objdata = create_object_data(tsurf, drogon_exportdata._export_config)

    buffer = BytesIO()
    export_object(objdata, buffer)
    buffer.seek(0)

    assert buffer.read(14).decode("utf-8") == "GOCAD TSurf 1\n"


def test_table_invalid_format_raises(
    dataframe: pd.DataFrame, mock_exportdata: ExportData
) -> None:
    """Invalid table format raises ConfigurationError."""
    mock_exportdata.table_fformat = "roff"

    with pytest.raises(ConfigurationError):
        _ = create_object_data(dataframe, mock_exportdata._export_config).extension

    mock_exportdata.table_fformat = "csv"  # reset


def test_compute_md5_and_size(
    gridproperty: xtgeo.GridProperty, mock_exportdata: ExportData
) -> None:
    """MD5 and size computation matches metadata."""
    objdata = create_object_data(gridproperty, mock_exportdata._export_config)

    metadata = mock_exportdata.generate_metadata(gridproperty)
    checksum, size = compute_md5_and_size(objdata)

    assert metadata["file"]["checksum_md5"] == checksum
    assert metadata["file"]["size_bytes"] == size


def test_preprocessed_observation_workflow(
    runpath_prehook: Path,
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
        runpath_prehook: Path, surfacepath: Path, monkeypatch: MonkeyPatch
    ) -> dict[str, Any]:
        """Run FMU workflow, using the preprocessed data as case data.

        When re-using metadata, the input object to dataio shall not be a XTGeo or
        Pandas or ... instance, but just a file path (either as string or a pathlib.Path
        object). This is because we want to avoid time and resources spent on double
        reading e.g. a seismic cube, but rather trigger a file copy action instead.

        But it requires that valid metadata for that file is found. The rule for
        merging is currently defaulted to "preprocessed".
        """
        monkeypatch.chdir(runpath_prehook)

        casepath = runpath_prehook
        edata = dataio.ExportPreprocessedData(is_observation=True, casepath=casepath)
        return edata.generate_metadata(surfacepath)

    # run two stage process
    remove_ert_env()
    edata, mysurf = _export_data_from_rms(
        rmssetup, rmsglobalconfig, regsurf, monkeypatch
    )
    set_ert_env_prehook()
    case_meta = _run_case_fmu(runpath_prehook, mysurf, monkeypatch)

    out = Path(mysurf)
    with open(out.parent / f".{out.name}.yml", encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    assert metadata["data"] == case_meta["data"]
