"""Test the _MetaData class from the _metadata.py module"""

import logging
from copy import deepcopy

import fmu.dataio as dio
import pytest
from fmu.dataio._metadata import (
    SCHEMA,
    SOURCE,
    VERSION,
    generate_export_metadata,
)
from fmu.dataio._utils import prettyprint_dict
from fmu.dataio.datastructure.meta.meta import (
    SystemInformationOperatingSystem,
    TracklogEvent,
)
from fmu.dataio.providers.objectdata._provider import objectdata_provider_factory

# pylint: disable=no-member

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# DOLLAR block
# --------------------------------------------------------------------------------------


def test_metadata_dollars(edataobj1, regsurf):
    """Testing the dollars part which is hard set."""

    mymeta = edataobj1.generate_metadata(obj=regsurf)

    assert mymeta["version"] == VERSION
    assert mymeta["$schema"] == SCHEMA
    assert mymeta["source"] == SOURCE


# --------------------------------------------------------------------------------------
# Tracklog
# --------------------------------------------------------------------------------------


def test_generate_meta_tracklog_fmu_dataio_version(regsurf, edataobj1):
    mymeta = generate_export_metadata(regsurf, edataobj1)
    tracklog = mymeta["tracklog"]

    assert isinstance(tracklog, list)
    assert len(tracklog) == 1  # assume "created"

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert parsed.event == "created"

    # datetime in tracklog shall include time zone offset
    assert parsed.datetime.tzinfo is not None

    # datetime in tracklog shall be on UTC time
    assert parsed.datetime.utcoffset().total_seconds() == 0

    assert parsed.sysinfo.fmu_dataio is not None
    assert parsed.sysinfo.fmu_dataio.version is not None


def test_generate_meta_tracklog_komodo_version(edataobj1, regsurf, monkeypatch):
    fake_komodo_release = "<FAKE_KOMODO_RELEASE_VERSION>"
    monkeypatch.setenv("KOMODO_RELEASE", fake_komodo_release)

    mymeta = generate_export_metadata(regsurf, edataobj1)
    tracklog = mymeta["tracklog"]

    assert isinstance(tracklog, list)
    assert len(tracklog) == 1  # assume "created"

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert parsed.event == "created"

    # datetime in tracklog shall include time zone offset
    assert parsed.datetime.tzinfo is not None

    # datetime in tracklog shall be on UTC time
    assert parsed.datetime.utcoffset().total_seconds() == 0

    assert parsed.sysinfo.komodo is not None
    assert parsed.sysinfo.komodo.version == fake_komodo_release


def test_generate_meta_tracklog_operating_system(edataobj1, regsurf):
    mymeta = generate_export_metadata(regsurf, edataobj1)
    tracklog = mymeta["tracklog"]

    assert isinstance(tracklog, list)
    assert len(tracklog) == 1  # assume "created"

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert isinstance(
        parsed.sysinfo.operating_system,
        SystemInformationOperatingSystem,
    )


# --------------------------------------------------------------------------------------
# DATA block (ObjectData)
# --------------------------------------------------------------------------------------


def test_populate_meta_objectdata(regsurf, edataobj2):
    mymeta = generate_export_metadata(regsurf, edataobj2)
    objdata = objectdata_provider_factory(regsurf, edataobj2)

    assert objdata.name == "VOLANTIS GP. Top"
    assert mymeta["display"]["name"] == objdata.name
    assert edataobj2.name == "TopVolantis"

    # surfaces shall have data.spec
    assert mymeta["data"]
    assert mymeta["data"]["spec"]
    assert mymeta["data"]["spec"] == objdata.get_spec().model_dump(
        mode="json",
        exclude_none=True,
    )


def test_bbox_zmin_zmax_presence(polygons, edataobj2):
    """
    Test to ensure the zmin/zmax fields are present in the metadata for a
    data type (polygons) where it is expexted. This is dependent on the order
    of the bbox types (2D/3D) inside the pydantic model. If 2D is first zmin/zmax
    will be ignored even if present.
    """
    mymeta = generate_export_metadata(polygons, edataobj2)

    # polygons shall have data.spec
    assert "zmin" in mymeta["data"]["bbox"]
    assert "zmax" in mymeta["data"]["bbox"]


def test_populate_meta_undef_is_zero(regsurf, globalconfig2):
    eobj1 = dio.ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content="depth",
        unit="m",
    )

    # assert field is present and default is False
    mymeta1 = eobj1.generate_metadata(regsurf)
    assert mymeta1["data"]["undef_is_zero"] is False

    # assert that value is reflected when passed to generate_metadata
    mymeta2 = eobj1.generate_metadata(regsurf, undef_is_zero=True)
    assert mymeta2["data"]["undef_is_zero"] is True

    # assert that value is reflected when passed to ExportData
    eobj2 = dio.ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content="depth",
        unit="m",
        undef_is_zero=True,
    )
    mymeta3 = eobj2.generate_metadata(regsurf, undef_is_zero=True)
    assert mymeta3["data"]["undef_is_zero"] is True


# --------------------------------------------------------------------------------------
# MASTERDATA block
# --------------------------------------------------------------------------------------


def test_metadata_populate_masterdata_is_empty(globalconfig1, regsurf):
    """Testing the masterdata part, first with no settings."""
    config = deepcopy(globalconfig1)
    del config["masterdata"]  # to force missing masterdata

    some = dio.ExportData(config=config, content="depth")

    assert not some._config_is_valid

    mymeta = generate_export_metadata(regsurf, some)
    assert "masterdata" not in mymeta


def test_metadata_populate_masterdata_is_present_ok(edataobj1, edataobj2, regsurf):
    """Testing the masterdata part with OK metdata."""

    mymeta = generate_export_metadata(regsurf, edataobj1)
    assert mymeta["masterdata"] == edataobj1.config["masterdata"]

    mymeta = generate_export_metadata(regsurf, edataobj2)
    assert mymeta["masterdata"] == edataobj2.config["masterdata"]


# --------------------------------------------------------------------------------------
# ACCESS block
# --------------------------------------------------------------------------------------


def test_metadata_populate_access_miss_cfg_access(globalconfig1, regsurf):
    """Testing the access part, now with config missing access."""

    cfg1_edited = deepcopy(globalconfig1)
    del cfg1_edited["access"]

    edata = dio.ExportData(config=cfg1_edited, content="depth")
    assert not edata._config_is_valid

    mymeta = generate_export_metadata(regsurf, edata)
    # check that the default "internal" is used
    assert mymeta["access"]["classification"] == "internal"


def test_metadata_populate_access_ok_config(edataobj2, regsurf):
    """Testing the access part, now with config ok access."""

    mymeta = generate_export_metadata(regsurf, edataobj2)
    assert mymeta["access"] == {
        "asset": {"name": "Drogon"},
        "ssdl": {"access_level": "internal", "rep_include": True},
        "classification": "internal",
    }


def test_metadata_populate_from_argument(globalconfig1, regsurf):
    """Testing the access part, now with ok config and a change in access."""

    # test assumptions
    assert globalconfig1["access"]["classification"] == "internal"

    edata = dio.ExportData(
        config=globalconfig1,
        access_ssdl={"access_level": "restricted", "rep_include": True},
        content="depth",
    )
    mymeta = generate_export_metadata(regsurf, edata)

    assert mymeta["access"] == {
        "asset": {"name": "Test"},
        "ssdl": {"access_level": "restricted", "rep_include": True},
        "classification": "restricted",  # mirroring ssdl.access_level
    }


def test_metadata_populate_partial_access_ssdl(globalconfig1, regsurf):
    """Test what happens if ssdl_access argument is partial."""

    # test assumptions
    assert globalconfig1["access"]["classification"] == "internal"
    assert globalconfig1["access"]["ssdl"]["rep_include"] is False

    # rep_include only, but in config
    edata = dio.ExportData(
        config=globalconfig1, access_ssdl={"rep_include": True}, content="depth"
    )

    mymeta = generate_export_metadata(regsurf, edata)
    assert mymeta["access"]["ssdl"]["rep_include"] is True
    assert mymeta["access"]["ssdl"]["access_level"] == "internal"  # default
    assert mymeta["access"]["classification"] == "internal"  # default

    # access_level only, but in config
    edata = dio.ExportData(
        config=globalconfig1,
        access_ssdl={"access_level": "restricted"},
        content="depth",
    )
    mymeta = generate_export_metadata(regsurf, edata)
    assert mymeta["access"]["ssdl"]["rep_include"] is False  # default
    assert mymeta["access"]["ssdl"]["access_level"] == "restricted"
    assert mymeta["access"]["classification"] == "restricted"


def test_metadata_populate_wrong_config(globalconfig1, regsurf):
    """Test error in access_ssdl in config."""

    # test assumptions
    _config = deepcopy(globalconfig1)
    _config["access"]["classification"] = "wrong"

    with pytest.warns(UserWarning):
        edata = dio.ExportData(config=_config, content="depth")

    assert not edata._config_is_valid

    # use default 'internal' if wrong in config
    meta = generate_export_metadata(regsurf, edata)
    assert meta["access"]["classification"] == "internal"


def test_metadata_populate_wrong_argument(globalconfig1):
    """Test error in access_ssdl in arguments."""

    with pytest.raises(ValueError, match="is not a valid AccessLevel"):
        dio.ExportData(
            config=globalconfig1,
            access_ssdl={"access_level": "wrong"},
            content="depth",
        )


def test_metadata_access_correct_input(globalconfig1, regsurf):
    """Test giving correct input."""
    # Input is "restricted" and False - correct use, shall work
    edata = dio.ExportData(
        config=globalconfig1,
        content="depth",
        access_ssdl={"access_level": "restricted", "rep_include": False},
    )
    mymeta = generate_export_metadata(regsurf, edata)
    assert mymeta["access"]["ssdl"]["rep_include"] is False
    assert mymeta["access"]["ssdl"]["access_level"] == "restricted"
    assert mymeta["access"]["classification"] == "restricted"

    # Input is "internal" and True - correct use, shall work
    edata = dio.ExportData(
        config=globalconfig1,
        content="depth",
        access_ssdl={"access_level": "internal", "rep_include": True},
    )
    mymeta = generate_export_metadata(regsurf, edata)
    assert mymeta["access"]["ssdl"]["rep_include"] is True
    assert mymeta["access"]["ssdl"]["access_level"] == "internal"
    assert mymeta["access"]["classification"] == "internal"


def test_metadata_access_deprecated_input(globalconfig1, regsurf):
    """Test giving deprecated input."""
    # Input is "asset". Is deprecated, shall work with warning.
    # Output shall be "restricted".
    with pytest.warns(
        FutureWarning,
        match="The value 'asset' for access.ssdl.access_level is deprec",
    ):
        edata = dio.ExportData(
            config=globalconfig1,
            access_ssdl={"access_level": "asset"},
            content="depth",
        )
    assert edata._config_is_valid

    mymeta = generate_export_metadata(regsurf, edata)
    assert mymeta["access"]["ssdl"]["access_level"] == "restricted"
    assert mymeta["access"]["classification"] == "restricted"


def test_metadata_access_illegal_input(globalconfig1):
    """Test giving illegal input, should provide empty access field"""

    # Input is "secret"
    with pytest.raises(ValueError, match="is not a valid AccessLevel"):
        dio.ExportData(
            config=globalconfig1,
            access_ssdl={"access_level": "secret"},
            content="depth",
        )

    # Input is "open". Not allowed, shall fail.
    with pytest.raises(ValueError, match="is not a valid AccessLevel"):
        dio.ExportData(
            config=globalconfig1,
            access_ssdl={"access_level": "open"},
            content="depth",
        )


def test_metadata_access_no_input(globalconfig1, regsurf):
    """Test not giving any input arguments."""

    # test assumption, deprected access.ssdl.access_level not present in config
    assert "access_level" not in globalconfig1["access"]["ssdl"]

    # No input, revert to config
    configcopy = deepcopy(globalconfig1)
    configcopy["access"]["classification"] = "restricted"
    configcopy["access"]["ssdl"]["rep_include"] = True
    edata = dio.ExportData(config=configcopy, content="depth")
    mymeta = generate_export_metadata(regsurf, edata)
    assert mymeta["access"]["ssdl"]["rep_include"] is True
    assert mymeta["access"]["ssdl"]["access_level"] == "restricted"
    assert mymeta["access"]["classification"] == "restricted"  # mirrored

    # No input, no config, shall default to "internal" and False
    configcopy = deepcopy(globalconfig1)
    del configcopy["access"]["classification"]
    del configcopy["access"]["ssdl"]["rep_include"]
    edata = dio.ExportData(config=globalconfig1, content="depth")
    mymeta = generate_export_metadata(regsurf, edata)
    assert mymeta["access"]["ssdl"]["rep_include"] is False  # default
    assert mymeta["access"]["ssdl"]["access_level"] == "internal"  # default
    assert mymeta["access"]["classification"] == "internal"  # mirrored


# --------------------------------------------------------------------------------------
# DISPLAY block
# --------------------------------------------------------------------------------------


def test_metadata_display_name_not_given(regsurf, edataobj2):
    """Test that display.name == data.name when not explicitly provided."""

    mymeta = generate_export_metadata(regsurf, edataobj2)
    objdata = objectdata_provider_factory(regsurf, edataobj2)

    assert "name" in mymeta["display"]
    assert mymeta["display"]["name"] == objdata.name


def test_metadata_display_name_given(regsurf, edataobj2):
    """Test that display.name is set when explicitly given."""

    edataobj2.display_name = "My Display Name"

    mymeta = generate_export_metadata(regsurf, edataobj2)
    objdata = objectdata_provider_factory(regsurf, edataobj2)

    assert mymeta["display"]["name"] == "My Display Name"
    assert objdata.name == "VOLANTIS GP. Top"


# --------------------------------------------------------------------------------------
# The GENERATE method
# --------------------------------------------------------------------------------------


def test_generate_full_metadata(regsurf, edataobj2):
    """Generating the full metadata block for a xtgeo surface."""

    metadata_result = generate_export_metadata(
        regsurf, edataobj2, skip_null=False
    )  # want to have None

    logger.debug("\n%s", prettyprint_dict(metadata_result))

    # check some samples
    assert metadata_result["masterdata"]["smda"]["country"][0]["identifier"] == "Norway"
    assert metadata_result["access"]["ssdl"]["access_level"] == "internal"
    assert metadata_result["data"]["unit"] == "m"
