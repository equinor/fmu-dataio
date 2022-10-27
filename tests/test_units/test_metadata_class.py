"""Test the _MetaData class from the _metadata.py module"""
import logging
from copy import deepcopy

import pytest

import fmu.dataio as dio
from fmu.dataio._metadata import SCHEMA, SOURCE, VERSION, ConfigurationError, _MetaData
from fmu.dataio._utils import prettyprint_dict

# pylint: disable=no-member

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# DOLLAR block
# --------------------------------------------------------------------------------------


def test_metadata_dollars(edataobj1):
    """Testing the dollars part which is hard set."""

    mymeta = _MetaData("dummy", edataobj1)

    assert mymeta.meta_dollars["version"] == VERSION
    assert mymeta.meta_dollars["$schema"] == SCHEMA
    assert mymeta.meta_dollars["source"] == SOURCE


# --------------------------------------------------------------------------------------
# DATA block (ObjectData)
# --------------------------------------------------------------------------------------


def test_populate_meta_objectdata(regsurf, edataobj2):
    mymeta = _MetaData(regsurf, edataobj2)
    mymeta._populate_meta_objectdata()
    assert mymeta.objdata.name == "VOLANTIS GP. Top"


def test_populate_meta_undef_is_zero(regsurf, globalconfig2):

    eobj1 = dio.ExportData(
        config=globalconfig2,
        name="TopVolantis",
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
        unit="m",
        undef_is_zero=True,
    )
    mymeta3 = eobj2.generate_metadata(regsurf, undef_is_zero=True)
    assert mymeta3["data"]["undef_is_zero"] is True


# --------------------------------------------------------------------------------------
# MASTERDATA block
# --------------------------------------------------------------------------------------


def test_metadata_populate_masterdata_is_empty(globalconfig1):
    """Testing the masterdata part, first with no settings."""

    some = dio.ExportData(config=globalconfig1)
    del some.config["masterdata"]  # to force missing masterdata

    mymeta = _MetaData("dummy", some)

    with pytest.warns(UserWarning):
        mymeta._populate_meta_masterdata()
    assert mymeta.meta_masterdata is None


def test_metadata_populate_masterdata_is_present_ok(edataobj1, edataobj2):
    """Testing the masterdata part with OK metdata."""

    mymeta = _MetaData("dummy", edataobj1)
    mymeta._populate_meta_masterdata()
    assert mymeta.meta_masterdata == edataobj1.config["masterdata"]

    mymeta = _MetaData("dummy", edataobj2)
    mymeta._populate_meta_masterdata()
    assert mymeta.meta_masterdata == edataobj2.config["masterdata"]


# --------------------------------------------------------------------------------------
# ACCESS block
# --------------------------------------------------------------------------------------


def test_metadata_populate_access_miss_config_access(edataobj1):
    """Testing the access part, now with config missing access."""

    cfg1_edited = deepcopy(edataobj1)
    del cfg1_edited.config["access"]

    mymeta = _MetaData("dummy", cfg1_edited)

    with pytest.raises(ConfigurationError):
        mymeta._populate_meta_access()


def test_metadata_populate_access_ok_config(edataobj2):
    """Testing the access part, now with config ok access."""

    mymeta = _MetaData("dummy", edataobj2)

    mymeta._populate_meta_access()
    assert mymeta.meta_access == {
        "asset": {"name": "Drogon"},
        "ssdl": {"access_level": "internal", "rep_include": True},
    }


def test_metadata_populate_change_access_ok(globalconfig1):
    """Testing the access part, now with ok config and a change in access."""

    edata = dio.ExportData(
        config=globalconfig1,
        access_ssdl={"access_level": "paranoid", "rep_include": False},
    )
    mymeta = _MetaData("dummy", edata)

    mymeta._populate_meta_access()
    assert mymeta.meta_access == {
        "asset": {"name": "Test"},
        "ssdl": {"access_level": "paranoid", "rep_include": False},
    }


# --------------------------------------------------------------------------------------
# The GENERATE method
# --------------------------------------------------------------------------------------


def test_generate_full_metadata(regsurf, edataobj2):
    """Generating the full metadata block for a xtgeo surface."""

    mymeta = _MetaData(regsurf, edataobj2)

    metadata_result = mymeta.generate_export_metadata(
        skip_null=False
    )  # want to have None

    logger.debug("\n%s", prettyprint_dict(metadata_result))

    # check some samples
    assert metadata_result["masterdata"]["smda"]["country"][0]["identifier"] == "Norway"
    assert metadata_result["access"]["ssdl"]["access_level"] == "internal"
    assert metadata_result["data"]["unit"] == "m"
