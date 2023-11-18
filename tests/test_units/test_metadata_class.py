"""Test the _MetaData class from the _metadata.py module"""
import logging
from copy import deepcopy
import os

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


def test_metadata_populate_masterdata_is_empty(globalconfig1):
    """Testing the masterdata part, first with no settings."""

    some = dio.ExportData(config=globalconfig1, content="depth")
    del some.config["masterdata"]  # to force missing masterdata

    mymeta = _MetaData("dummy", some)

    with pytest.raises(ValueError, match="A config exists, but 'masterdata' are not"):
        mymeta._populate_meta_masterdata()


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
        "classification": "internal",
    }


def test_metadata_populate_from_argument(globalconfig1):
    """Testing the access part, now with ok config and a change in access."""

    # test assumptions
    assert globalconfig1["access"]["ssdl"]["access_level"] == "internal"

    edata = dio.ExportData(
        config=globalconfig1,
        access_ssdl={"access_level": "restricted", "rep_include": True},
        content="depth",
    )
    mymeta = _MetaData("dummy", edata)

    mymeta._populate_meta_access()
    assert mymeta.meta_access == {
        "asset": {"name": "Test"},
        "ssdl": {"access_level": "restricted", "rep_include": True},
        "classification": "restricted",  # mirroring ssdl.access_level
    }


def test_metadata_populate_partial_access_ssdl(globalconfig1):
    """Test what happens if ssdl_access argument is partial."""

    # test assumptions
    assert globalconfig1["access"]["ssdl"]["access_level"] == "internal"
    assert globalconfig1["access"]["ssdl"]["rep_include"] is False

    # rep_include only, but in config
    edata = dio.ExportData(
        config=globalconfig1, access_ssdl={"rep_include": True}, content="depth"
    )
    mymeta = _MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is True
    assert mymeta.meta_access["ssdl"]["access_level"] == "internal"  # default
    assert mymeta.meta_access["classification"] == "internal"  # default

    # access_level only, but in config
    edata = dio.ExportData(
        config=globalconfig1,
        access_ssdl={"access_level": "restricted"},
        content="depth",
    )
    mymeta = _MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is False  # default
    assert mymeta.meta_access["ssdl"]["access_level"] == "restricted"
    assert mymeta.meta_access["classification"] == "restricted"


def test_metadata_populate_wrong_config(globalconfig1):
    """Test error in access_ssdl in config."""

    # test assumptions
    _config = deepcopy(globalconfig1)
    _config["access"]["ssdl"]["access_level"] = "wrong"

    edata = dio.ExportData(config=_config, content="depth")
    mymeta = _MetaData("dummy", edata)
    with pytest.raises(ConfigurationError, match="Illegal value for access"):
        mymeta._populate_meta_access()


def test_metadata_populate_wrong_argument(globalconfig1):
    """Test error in access_ssdl in arguments."""

    edata = dio.ExportData(
        config=globalconfig1, access_ssdl={"access_level": "wrong"}, content="depth"
    )
    mymeta = _MetaData("dummy", edata)
    with pytest.raises(ConfigurationError, match="Illegal value for access"):
        mymeta._populate_meta_access()


def test_metadata_access_correct_input(globalconfig1):
    """Test giving correct input."""
    # Input is "restricted" and False - correct use, shall work
    edata = dio.ExportData(
        config=globalconfig1,
        content="depth",
        access_ssdl={"access_level": "restricted", "rep_include": False},
    )
    mymeta = _MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is False
    assert mymeta.meta_access["ssdl"]["access_level"] == "restricted"
    assert mymeta.meta_access["classification"] == "restricted"

    # Input is "internal" and True - correct use, shall work
    edata = dio.ExportData(
        config=globalconfig1,
        content="depth",
        access_ssdl={"access_level": "internal", "rep_include": True},
    )
    mymeta = _MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is True
    assert mymeta.meta_access["ssdl"]["access_level"] == "internal"
    assert mymeta.meta_access["classification"] == "internal"


def test_metadata_access_deprecated_input(globalconfig1):
    """Test giving deprecated input."""
    # Input is "asset". Is deprecated, shall work with warning.
    # Output shall be "restricted".
    edata = dio.ExportData(
        config=globalconfig1, access_ssdl={"access_level": "asset"}, content="depth"
    )
    mymeta = _MetaData("dummy", edata)
    with pytest.warns(
        UserWarning,
        match="The value 'asset' for access.ssdl.access_level is deprec",
    ):
        mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["access_level"] == "restricted"
    assert mymeta.meta_access["classification"] == "restricted"


def test_metadata_access_illegal_input(globalconfig1):
    """Test giving illegal input."""

    # Input is "secret". Not allowed, shall fail.
    edata = dio.ExportData(
        config=globalconfig1, access_ssdl={"access_level": "secret"}, content="depth"
    )
    mymeta = _MetaData("dummy", edata)
    with pytest.raises(ConfigurationError, match="Illegal value for access"):
        mymeta._populate_meta_access()

    # Input is "open". Not allowed, shall fail.
    edata = dio.ExportData(
        config=globalconfig1, access_ssdl={"access_level": "open"}, content="depth"
    )
    mymeta = _MetaData("dummy", edata)
    with pytest.raises(ConfigurationError, match="Illegal value for access"):
        mymeta._populate_meta_access()


def test_metadata_access_no_input(globalconfig1):
    """Test not giving any input arguments."""

    # No input, revert to config
    configcopy = deepcopy(globalconfig1)
    configcopy["access"]["ssdl"]["access_level"] = "restricted"
    configcopy["access"]["ssdl"]["rep_include"] = True
    edata = dio.ExportData(config=configcopy, content="depth")
    mymeta = _MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is True
    assert mymeta.meta_access["ssdl"]["access_level"] == "restricted"
    assert mymeta.meta_access["classification"] == "restricted"  # mirrored

    # No input, no config, shall default to "internal" and False
    configcopy = deepcopy(globalconfig1)
    del configcopy["access"]["ssdl"]["access_level"]
    del configcopy["access"]["ssdl"]["rep_include"]
    edata = dio.ExportData(config=globalconfig1, content="depth")
    mymeta = _MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is False  # default
    assert mymeta.meta_access["ssdl"]["access_level"] == "internal"  # default
    assert mymeta.meta_access["classification"] == "internal"  # mirrored


def test_metadata_access_rep_include(globalconfig1):
    """Test the input of the rep_include field."""


# --------------------------------------------------------------------------------------
# RELATIONS block
# --------------------------------------------------------------------------------------


def test_metadata_relations_no_collection_name(globalconfig1):
    "Test the relations generation when collection_name is not provided."
    edata = dio.ExportData(config=globalconfig1, content="depth")
    mymeta = _MetaData("dummy", edata)
    mymeta._populate_meta_relations()

    # no collection_name given, relations shall be None
    assert mymeta.dataio.collection_name is None
    assert mymeta.meta_relations is None


def test_metadata_relations_with_case_uuid(globalconfig1, fmurun_w_casemetadata):
    """Confirm collection changes with different case_uuids."""

    cname = "mycollection"

    # produce with original fmu.case.uuid
    edata = dio.ExportData(config=globalconfig1, content="depth", collection_name=cname)
    edata._rootpath = fmurun_w_casemetadata
    mymeta = _MetaData("dummy", edata, verbosity="DEBUG")
    mymeta._populate_meta_fmu()
    mymeta._populate_meta_relations()
    first = deepcopy(mymeta.meta_relations["collections"][0])
    assert len(mymeta.meta_relations["collections"]) == 1

    # produce again, verify identical
    mymeta._populate_meta_relations()
    same_as_first = deepcopy(mymeta.meta_relations["collections"][0])
    assert first == same_as_first

    # modify fmu.case.uuid and produce again
    newuuid = "b31b05e8-e47f-47b1-8fee-e94b2234aa21"
    mymeta.meta_fmu["case"]["uuid"] = newuuid
    mymeta._populate_meta_relations()
    second = deepcopy(mymeta.meta_relations["collections"][0])
    assert len(mymeta.meta_relations["collections"]) == 1

    # verify different
    assert first != second
    assert len(first) == len(second) == 36


def test_metadata_relations_one_collection_name(globalconfig1):
    """Test the relations generation when collection name is provided as list with one
    member. Also test that similar behaviour if list or not.

    collection_name = ["tst"] and collection_name = "tst" shall give same result.

    """

    # === Input as list[str]
    edata_list = dio.ExportData(
        config=globalconfig1, content="depth", collection_name=["tst"]
    )
    mymeta_list = _MetaData("dummy", edata_list, verbosity="DEBUG")
    mymeta_list._populate_meta_relations()

    assert "collections" in mymeta_list.meta_relations
    assert isinstance(mymeta_list.meta_relations["collections"], list)
    assert len(mymeta_list.meta_relations["collections"]) == 1

    collections_ref_list = mymeta_list.meta_relations["collections"][0]

    assert isinstance(collections_ref_list, str)
    assert len(collections_ref_list) == 36  # poor mans verification of uuid4

    # === Input as str
    edata_str = dio.ExportData(
        config=globalconfig1, content="depth", collection_name="tst"
    )
    mymeta_str = _MetaData("dummy", edata_str, verbosity="DEBUG")
    mymeta_str._populate_meta_relations()

    assert "collections" in mymeta_str.meta_relations
    assert isinstance(mymeta_str.meta_relations["collections"], list)
    assert len(mymeta_str.meta_relations["collections"]) == 1

    collections_ref_str = mymeta_str.meta_relations["collections"][0]

    assert isinstance(collections_ref_str, str)
    assert len(collections_ref_str) == 36  # poor mans verification of uuid4

    # === Confirm identical
    assert collections_ref_str == collections_ref_list


def test_metadata_relations_multiple_collection_name(globalconfig1):
    """Test the relations generation when multiple collection name is provided."""
    edata = dio.ExportData(
        config=globalconfig1, content="depth", collection_name=["tst", "tst2", "tst3"]
    )
    mymeta = _MetaData("dummy", edata)
    mymeta._populate_meta_relations()

    assert "collections" in mymeta.meta_relations
    assert isinstance(mymeta.meta_relations["collections"], list)
    assert len(mymeta.meta_relations["collections"]) == 3

    for collections_ref in mymeta.meta_relations["collections"]:
        assert isinstance(collections_ref, str)
        assert len(collections_ref) == 36  # poor mans verification of uuid4


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
