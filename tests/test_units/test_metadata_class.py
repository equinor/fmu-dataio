"""Test the _MetaData class from the _metadata.py module"""

import logging
from copy import deepcopy
from typing import Any

import pytest
import xtgeo
from fmu.datamodels.common.enums import TrackLogEventType
from fmu.datamodels.common.tracklog import (
    OperatingSystem,
    TracklogEvent,
)
from fmu.datamodels.fmu_results import FmuResultsSchema
from pytest import MonkeyPatch

import fmu.dataio as dio
from fmu.dataio._metadata import generate_export_metadata
from fmu.dataio._utils import prettyprint_dict, read_metadata_from_file
from fmu.dataio.dataio import ExportData
from fmu.dataio.providers.objectdata._provider import objectdata_provider_factory

# pylint: disable=no-member

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# DOLLAR block
# --------------------------------------------------------------------------------------


def test_metadata_dollars(
    mock_exportdata: ExportData, regsurf: xtgeo.RegularSurface
) -> None:
    """Testing the dollars part which is hard set."""

    mymeta = mock_exportdata.generate_metadata(obj=regsurf)

    assert mymeta["version"] == FmuResultsSchema.VERSION
    assert mymeta["$schema"] == FmuResultsSchema.url()
    assert mymeta["source"] == FmuResultsSchema.SOURCE

    # also check that it is preserved in the exported metadata
    exportpath = mock_exportdata.export(regsurf)
    exportmeta = read_metadata_from_file(exportpath)

    assert exportmeta["version"] == FmuResultsSchema.VERSION
    assert exportmeta["$schema"] == FmuResultsSchema.url()
    assert exportmeta["source"] == FmuResultsSchema.SOURCE


# --------------------------------------------------------------------------------------
# Tracklog
# --------------------------------------------------------------------------------------


def test_generate_meta_tracklog_fmu_dataio_version(
    regsurf: xtgeo.RegularSurface, mock_exportdata: ExportData
) -> None:
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, mock_exportdata._export_config)
    tracklog = mymeta.tracklog

    assert isinstance(tracklog.root, list)
    assert len(tracklog.root) == 1  # assume TrackLogEventType.created

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert parsed.event == TrackLogEventType.created

    # datetime in tracklog shall include time zone offset
    assert parsed.datetime.tzinfo is not None

    # datetime in tracklog shall be on UTC time
    assert parsed.datetime.utcoffset().total_seconds() == 0

    assert parsed.sysinfo is not None
    assert parsed.sysinfo.fmu_dataio is not None
    assert parsed.sysinfo.fmu_dataio.version == dio.__version__


def test_generate_meta_tracklog_komodo_version(
    mock_exportdata: dio.ExportData,
    regsurf: xtgeo.RegularSurface,
    monkeypatch: MonkeyPatch,
) -> None:
    fake_komodo_release = "<FAKE_KOMODO_RELEASE_VERSION>"
    monkeypatch.setenv("KOMODO_RELEASE", fake_komodo_release)

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, mock_exportdata._export_config)
    tracklog = mymeta.tracklog

    assert isinstance(tracklog.root, list)
    assert len(tracklog.root) == 1  # assume TrackLogEventType.created

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert parsed.event == TrackLogEventType.created

    # datetime in tracklog shall include time zone offset
    assert parsed.datetime.tzinfo is not None

    # datetime in tracklog shall be on UTC time
    assert parsed.datetime.utcoffset().total_seconds() == 0

    assert parsed.sysinfo is not None
    assert parsed.sysinfo.komodo is not None
    assert parsed.sysinfo.komodo.version == fake_komodo_release
    assert parsed.sysinfo.fmu_dataio is not None
    assert parsed.sysinfo.fmu_dataio.version == dio.__version__


def test_generate_meta_tracklog_backup_komodo_version(
    mock_exportdata: dio.ExportData,
    regsurf: xtgeo.RegularSurface,
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that we read the Komodo version from KOMODO_RELEASE_BACKUP if it's set."""
    komodo_release = "2123.01.01"
    monkeypatch.delenv("KOMODO_RELEASE", raising=False)
    monkeypatch.setenv("KOMODO_RELEASE_BACKUP", komodo_release)

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    metadata = generate_export_metadata(objdata, mock_exportdata._export_config)
    tracklog = TracklogEvent.model_validate(metadata.tracklog[0])
    assert tracklog.sysinfo is not None
    assert tracklog.sysinfo.komodo is not None
    assert tracklog.sysinfo.komodo.version == komodo_release
    assert tracklog.sysinfo.fmu_dataio is not None
    assert tracklog.sysinfo.fmu_dataio.version == dio.__version__


def test_generate_meta_tracklog_komodo_version_preferred_over_backup(
    mock_exportdata: dio.ExportData,
    regsurf: xtgeo.RegularSurface,
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that we read the Komodo version from KOMODO_RELEASE.

    This should be true even if KOMODO_RELEASE_BACKUP is set."""
    komodo_release = "2123.01.01"
    backup_komodo_release = "2123.01.02"  # Suppose it's botched.

    # Sanity check to make sure this test tests something if modified in the future
    assert komodo_release != backup_komodo_release

    monkeypatch.setenv("KOMODO_RELEASE", komodo_release)
    monkeypatch.setenv("KOMODO_RELEASE_BACKUP", backup_komodo_release)

    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    metadata = generate_export_metadata(objdata, mock_exportdata._export_config)
    tracklog = TracklogEvent.model_validate(metadata.tracklog[0])
    assert tracklog.sysinfo is not None
    assert tracklog.sysinfo.komodo is not None
    assert tracklog.sysinfo.komodo.version == komodo_release
    assert tracklog.sysinfo.fmu_dataio is not None
    assert tracklog.sysinfo.fmu_dataio.version == dio.__version__


def test_generate_meta_tracklog_operating_system(
    mock_exportdata: ExportData, regsurf: xtgeo.RegularSurface
) -> None:
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, mock_exportdata._export_config)
    tracklog = mymeta.tracklog

    assert isinstance(tracklog.root, list)
    assert len(tracklog.root) == 1  # assume TrackLogEventType.created

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert isinstance(
        parsed.sysinfo.operating_system,
        OperatingSystem,
    )


# --------------------------------------------------------------------------------------
# DATA block (ObjectData)
# --------------------------------------------------------------------------------------


def test_populate_meta_objectdata(
    regsurf: xtgeo.RegularSurface, drogon_exportdata: ExportData
) -> None:
    objdata = objectdata_provider_factory(regsurf, drogon_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, drogon_exportdata._export_config)

    # print(drogon_exportdata._export_config.name)
    assert objdata.name == "VOLANTIS GP. Top"
    assert mymeta.display.name == objdata.name
    assert drogon_exportdata.name == "TopVolantis"

    # surfaces shall have data.spec
    assert mymeta.data
    assert mymeta.data.root.spec
    assert mymeta.data.root.spec == objdata.get_spec()


def test_bbox_zmin_zmax_presence(
    polygons: xtgeo.Polygons, drogon_exportdata: ExportData
) -> None:
    """
    Test to ensure the zmin/zmax fields are present in the metadata for a
    data type (polygons) where it is expexted. This is dependent on the order
    of the bbox types (2D/3D) inside the pydantic model. If 2D is first zmin/zmax
    will be ignored even if present.
    """
    objdata = objectdata_provider_factory(polygons, drogon_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, drogon_exportdata._export_config)

    # polygons shall have data.spec
    assert mymeta.data.root.bbox.zmin is not None
    assert mymeta.data.root.bbox.zmin
    assert mymeta.data.root.bbox.zmax


def test_populate_meta_undef_is_zero(
    regsurf: xtgeo.RegularSurface, drogon_global_config: dict[str, Any]
) -> None:
    eobj1 = dio.ExportData(
        config=drogon_global_config,
        name="TopVolantis",
        content="depth",
        unit="m",
    )

    # assert field is present and default is False
    mymeta1 = eobj1.generate_metadata(regsurf)
    assert mymeta1["data"]["undef_is_zero"] is False

    # assert that value is reflected when passed to generate_metadata
    # and warning is issued to move the argument to initialization
    with pytest.warns(FutureWarning, match="move them up to initialization"):
        mymeta2 = eobj1.generate_metadata(regsurf, undef_is_zero=True)
    assert mymeta2["data"]["undef_is_zero"] is True

    # assert that value is reflected when passed to ExportData
    eobj2 = dio.ExportData(
        config=drogon_global_config,
        name="TopVolantis",
        content="depth",
        unit="m",
        undef_is_zero=True,
    )
    mymeta3 = eobj2.generate_metadata(regsurf)
    assert mymeta3["data"]["undef_is_zero"] is True


# --------------------------------------------------------------------------------------
# MASTERDATA block
# --------------------------------------------------------------------------------------


def test_metadata_populate_masterdata_is_empty(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Testing the masterdata part, first with no settings."""
    config = deepcopy(mock_global_config)
    del config["masterdata"]  # to force missing masterdata

    with pytest.warns(UserWarning, match="The global config"):
        some = dio.ExportData(config=config, content="depth")

    assert some._export_config.config is None

    objdata = objectdata_provider_factory(regsurf, some._export_config)
    mymeta = generate_export_metadata(objdata, some._export_config)
    assert "masterdata" not in mymeta


def test_metadata_populate_masterdata_is_present_ok(
    mock_exportdata: ExportData,
    drogon_exportdata: ExportData,
    regsurf: xtgeo.RegularSurface,
) -> None:
    """Testing the masterdata part with OK metdata."""
    objdata = objectdata_provider_factory(regsurf, mock_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, mock_exportdata._export_config)
    assert mymeta.masterdata == mock_exportdata._export_config.config.masterdata

    objdata = objectdata_provider_factory(regsurf, drogon_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, drogon_exportdata._export_config)
    assert mymeta.masterdata == drogon_exportdata._export_config.config.masterdata


# --------------------------------------------------------------------------------------
# ACCESS block
# --------------------------------------------------------------------------------------


def test_metadata_populate_access_miss_cfg_access(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Testing the access part, now with config missing access."""

    cfg1_edited = deepcopy(mock_global_config)
    del cfg1_edited["access"]
    with pytest.warns(UserWarning, match="The global config"):
        edata = dio.ExportData(config=cfg1_edited, content="depth")
    assert edata._export_config.config is None

    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    # check that the default "internal" is used
    assert mymeta.access.classification == "internal"


def test_metadata_populate_access_ok_config(
    drogon_exportdata: ExportData, regsurf: xtgeo.RegularSurface
) -> None:
    """Testing the access part, now with config ok access."""

    objdata = objectdata_provider_factory(regsurf, drogon_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, drogon_exportdata._export_config)
    assert mymeta.access.model_dump(mode="json", exclude_none=True) == {
        "asset": {"name": "Drogon"},
        "ssdl": {"access_level": "internal", "rep_include": True},
        "classification": "internal",
    }


def test_metadata_populate_from_argument(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Testing the access part, now with ok config and a change in access."""

    # test assumptions
    assert mock_global_config["access"]["classification"] == "internal"

    edata = dio.ExportData(
        config=mock_global_config,
        classification="restricted",
        rep_include=True,
        content="depth",
    )
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)

    assert mymeta.access.model_dump(mode="json", exclude_none=True) == {
        "asset": {"name": "Test"},
        "ssdl": {"access_level": "restricted", "rep_include": True},
        "classification": "restricted",  # mirroring ssdl.access_level
    }


def test_metadata_populate_partial_access_ssdl(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test what happens if ssdl_access argument is partial."""

    # test assumptions
    assert mock_global_config["access"]["classification"] == "internal"
    assert "ssdl" not in mock_global_config["access"]  # no ssdl.rep_include

    # rep_include only, but in config
    edata = dio.ExportData(config=mock_global_config, rep_include=True, content="depth")

    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is True
    assert mymeta.access.ssdl.access_level == "internal"  # default
    assert mymeta.access.classification == "internal"  # default

    # access_level only, but in config
    edata = dio.ExportData(
        config=mock_global_config,
        classification="restricted",
        content="depth",
    )
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is False  # default
    assert mymeta.access.ssdl.access_level == "restricted"
    assert mymeta.access.classification == "restricted"


def test_metadata_populate_wrong_config(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test error in access_ssdl in config."""

    # test assumptions
    _config = deepcopy(mock_global_config)
    _config["access"]["classification"] = "wrong"

    with pytest.warns(UserWarning):
        edata = dio.ExportData(config=_config, content="depth")

    assert edata._export_config.config is None

    # use default 'internal' if wrong in config
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    meta = generate_export_metadata(objdata, edata._export_config)
    assert meta.access is not None
    assert meta.access.classification == "internal"


def test_metadata_populate_wrong_argument(mock_global_config: dict[str, Any]) -> None:
    """Test error in access_ssdl in arguments."""

    with pytest.raises(ValueError, match="is not a valid Classification"):
        dio.ExportData(
            config=mock_global_config,
            classification="wrong",
            content="depth",
        )


def test_metadata_access_correct_input(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test giving correct input."""
    # Input is "restricted" and False - correct use, shall work
    edata = dio.ExportData(
        config=mock_global_config,
        content="depth",
        classification="restricted",
        rep_include=False,
    )
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is False
    assert mymeta.access.ssdl.access_level == "restricted"
    assert mymeta.access.classification == "restricted"

    # Input is "internal" and True - correct use, shall work
    edata = dio.ExportData(
        config=mock_global_config,
        content="depth",
        classification="internal",
        rep_include=True,
    )
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is True
    assert mymeta.access.ssdl.access_level == "internal"
    assert mymeta.access.classification == "internal"


def test_metadata_access_deprecated_input(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test giving deprecated input."""
    # Input is "asset". Is deprecated, shall work with warning.
    # Output shall be "restricted".
    with pytest.warns(
        FutureWarning,
        match="The value 'asset' for access.ssdl.access_level is deprec",
    ):
        edata = dio.ExportData(
            config=mock_global_config,
            classification="asset",
            content="depth",
        )
    assert edata.config

    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.access_level == "restricted"
    assert mymeta.access.classification == "restricted"


def test_metadata_access_illegal_input(mock_global_config: dict[str, Any]) -> None:
    """Test giving illegal input, should provide empty access field"""

    # Input is "secret"
    with pytest.raises(ValueError, match="is not a valid Classification"):
        dio.ExportData(
            config=mock_global_config,
            classification="secret",
            content="depth",
        )

    # Input is "open". Not allowed, shall fail.
    with pytest.raises(ValueError, match="is not a valid Classification"):
        dio.ExportData(
            config=mock_global_config,
            classification="open",
            content="depth",
        )


def test_metadata_access_no_input(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test not giving any input arguments."""

    # test assumption, deprected access.ssdl not present in config
    assert "ssdl" not in mock_global_config["access"]

    # No input, revert to config
    configcopy = deepcopy(mock_global_config)
    configcopy["access"]["classification"] = "restricted"
    configcopy["access"]["ssdl"] = {"rep_include": True}
    # rep_include from config is deprecated
    with pytest.warns(FutureWarning, match="Use the 'rep_include' argument"):
        edata = dio.ExportData(config=configcopy, content="depth")
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is True
    assert mymeta.access.ssdl.access_level == "restricted"
    assert mymeta.access.classification == "restricted"  # mirrored

    # No input, no config, shall default to "internal" and False
    configcopy = deepcopy(mock_global_config)
    del configcopy["access"]["classification"]
    edata = dio.ExportData(config=mock_global_config, content="depth")
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is False  # default
    assert mymeta.access.ssdl.access_level == "internal"  # default
    assert mymeta.access.classification == "internal"  # mirrored


def test_metadata_rep_include_deprecation(
    mock_global_config: dict[str, Any], regsurf: xtgeo.RegularSurface
) -> None:
    """Test warnings for deprecated rep_include field in config."""
    configcopy = deepcopy(mock_global_config)
    # add rep_include to the config
    configcopy["access"]["ssdl"] = {"rep_include": True}
    with pytest.warns(FutureWarning, match="'rep_include' argument"):
        edata = dio.ExportData(config=configcopy, content="depth")
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is True

    configcopy["access"]["ssdl"] = {"rep_include": False}
    with pytest.warns(FutureWarning, match="'rep_include' argument"):
        edata = dio.ExportData(config=configcopy, content="depth")
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is False

    # check that default value is used if not present
    del configcopy["access"]["ssdl"]["rep_include"]
    edata = dio.ExportData(config=mock_global_config, content="depth")
    objdata = objectdata_provider_factory(regsurf, edata._export_config)
    mymeta = generate_export_metadata(objdata, edata._export_config)
    assert mymeta.access is not None
    assert mymeta.access.ssdl.rep_include is False  # default


# --------------------------------------------------------------------------------------
# DISPLAY block
# --------------------------------------------------------------------------------------


def test_metadata_display_name_not_given(
    regsurf: xtgeo.RegularSurface, drogon_exportdata: ExportData
) -> None:
    """Test that display.name == data.name when not explicitly provided."""

    objdata = objectdata_provider_factory(regsurf, drogon_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, drogon_exportdata._export_config)

    assert mymeta.display.name == objdata.name


def test_metadata_display_name_given(
    regsurf: xtgeo.RegularSurface, drogon_exportdata: ExportData
) -> None:
    """Test that display.name is set when explicitly given."""

    drogon_exportdata.display_name = "My Display Name"

    objdata = objectdata_provider_factory(regsurf, drogon_exportdata._export_config)
    mymeta = generate_export_metadata(objdata, drogon_exportdata._export_config)

    assert mymeta.display.name == "My Display Name"
    assert objdata.name == "VOLANTIS GP. Top"


# --------------------------------------------------------------------------------------
# The GENERATE method
# --------------------------------------------------------------------------------------


def test_generate_full_metadata(
    regsurf: xtgeo.RegularSurface, drogon_exportdata: ExportData
) -> None:
    """Generating the full metadata block for a xtgeo surface."""

    objdata = objectdata_provider_factory(regsurf, drogon_exportdata._export_config)
    metadata_result = generate_export_metadata(
        objdata, drogon_exportdata._export_config
    )

    logger.debug("\n%s", prettyprint_dict(metadata_result))

    # check some samples
    assert metadata_result is not None
    assert metadata_result.masterdata is not None
    assert metadata_result.access is not None
    assert metadata_result.masterdata.smda.country[0].identifier == "Norway"
    assert metadata_result.access.ssdl.access_level == "internal"
    assert metadata_result.data.root.unit == "m"
