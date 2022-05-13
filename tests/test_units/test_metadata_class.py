"""Test the _MetaData class from the _metadata.py module"""
import logging
from copy import deepcopy

import pytest

from fmu.dataio._metadata import (
    SCHEMA,
    SOURCE,
    VERSION,
    ConfigurationError,
    _MetaData,
)
from fmu.dataio._utils import C, G, S, X, prettyprint_dict

# pylint: disable=no-member

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# DOLLAR block
# --------------------------------------------------------------------------------------


def test_metadata_dollars(internalcfg1):
    """Testing the dollars part which is hard set."""

    mymeta = _MetaData("dummy", internalcfg1)

    assert mymeta.meta_dollars["version"] == VERSION
    assert mymeta.meta_dollars["$schema"] == SCHEMA
    assert mymeta.meta_dollars["source"] == SOURCE


# --------------------------------------------------------------------------------------
# DATA block (ObjectData)
# --------------------------------------------------------------------------------------


def test_populate_meta_objectdata(regsurf, internalcfg2):
    mymeta = _MetaData(regsurf, internalcfg2)
    mymeta._populate_meta_objectdata()
    assert mymeta.objdata.name == "VOLANTIS GP. Top"


# --------------------------------------------------------------------------------------
# MASTERDATA block
# --------------------------------------------------------------------------------------


def test_metadata_populate_masterdata_is_empty():
    """Testing the masterdata part, first with no settings."""

    mymeta = _MetaData("dummy", {S: None, G: None, C: None, X: None})

    with pytest.warns(UserWarning):
        mymeta._populate_meta_masterdata()


def test_metadata_populate_masterdata_is_present_ok(internalcfg1, internalcfg2):
    """Testing the masterdata part with OK metdata."""

    mymeta = _MetaData("dummy", internalcfg1)
    mymeta._populate_meta_masterdata()
    assert mymeta.meta_masterdata == internalcfg1[G]["masterdata"]

    mymeta = _MetaData("dummy", internalcfg2)
    mymeta._populate_meta_masterdata()
    assert mymeta.meta_masterdata == internalcfg2[G]["masterdata"]


# --------------------------------------------------------------------------------------
# ACCESS block
# --------------------------------------------------------------------------------------


def test_metadata_populate_access_miss_config_access(internalcfg1):
    """Testing the access part, now with config missing access."""

    cfg1_edited = deepcopy(internalcfg1)
    del cfg1_edited[G]["access"]

    mymeta = _MetaData("dummy", cfg1_edited)

    with pytest.raises(ConfigurationError):
        mymeta._populate_meta_access()


def test_metadata_populate_access_ok_config(internalcfg2):
    """Testing the access part, now with config missing access."""

    mymeta = _MetaData("dummy", internalcfg2)

    mymeta._populate_meta_access()
    assert mymeta.meta_access == {
        "asset": {"name": "Drogon"},
        "ssdl": {"access_level": "internal", "rep_include": True},
    }


def test_metadata_populate_change_access_ok(internalcfg2):
    """Testing the access part, now with ok config and a change in access."""

    mymeta = _MetaData("dummy", internalcfg2)

    mymeta._populate_meta_access()
    assert mymeta.meta_access == {
        "asset": {"name": "Drogon"},
        "ssdl": {"access_level": "internal", "rep_include": True},
    }


# --------------------------------------------------------------------------------------
# The GENERATE method
# --------------------------------------------------------------------------------------


def test_generate_full_metadata(regsurf, internalcfg2):
    """Generating the full metadata block for a xtgeo surface."""

    mymeta = _MetaData(regsurf, internalcfg2)

    metadata_result = mymeta.generate_export_metadata(
        skip_null=False
    )  # want to have None

    logger.debug("\n%s", prettyprint_dict(metadata_result))

    # check some samples
    assert metadata_result["masterdata"]["smda"]["country"][0]["identifier"] == "Norway"
    assert metadata_result["access"]["ssdl"]["access_level"] == "internal"
    assert metadata_result["data"]["unit"] == "m"
