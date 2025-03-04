"""Test the dataio ExportData etc from the dataio.py module."""

import logging
import os
import pathlib
import sys
from copy import deepcopy
from pathlib import Path

import pydantic
import pytest
import yaml

from fmu.dataio._models.fmu_results.enums import FMUContext, StandardResultName
from fmu.dataio._models.fmu_results.standard_result import InplaceVolumesStandardResult
from fmu.dataio._utils import (
    convert_datestr_to_isoformat,
    prettyprint_dict,
)
from fmu.dataio.dataio import ExportData, read_metadata
from fmu.dataio.providers._fmu import FmuEnv

# pylint: disable=no-member

logger = logging.getLogger(__name__)


def test_generate_metadata_simple(globalconfig1):
    """Test generating metadata"""

    default_fformat = ExportData.grid_fformat
    ExportData.grid_fformat = "grdecl"

    logger.info("Config in: \n%s", globalconfig1)

    edata = ExportData(config=globalconfig1, content="depth")

    assert edata.config.model.name == "Test"

    assert edata.meta_format is None
    assert edata.grid_fformat == "grdecl"
    assert edata.name == ""

    ExportData.grid_fformat = default_fformat  # reset


def test_missing_or_wrong_config_exports_with_warning(monkeypatch, tmp_path, regsurf):
    """In case a config is missing, or is invalid, do export with warning."""

    monkeypatch.chdir(tmp_path)

    with pytest.warns(UserWarning, match="The global config"):
        edata = ExportData(config={}, content="depth", name="mysurface")

    with pytest.warns(FutureWarning):
        meta = edata.generate_metadata(regsurf)
    assert "masterdata" not in meta

    # check that obj is created but no metadata is found
    with pytest.warns(UserWarning, match="without metadata"):
        out = edata.export(regsurf)
    assert "mysurface" in out
    assert Path(out).exists()
    with pytest.raises(OSError, match="Cannot find requested metafile"):
        read_metadata(out)


@pytest.mark.skip_inside_rmsvenv
def test_wrong_config_exports_correctly_ouside_fmu(
    monkeypatch, tmp_path, globalconfig1, regsurf
):
    """
    In case a config is invalid, objects are exported without metadata.
    Test that the export path is correct and equal one with valid config,
    outside an fmu run.
    """

    # TODO: Refactor tests and move away from outside/inside rms pattern

    monkeypatch.chdir(tmp_path)
    name = "mysurface"

    with pytest.warns(UserWarning, match="The global config"), pytest.warns(
        UserWarning, match="without metadata"
    ):
        objpath_cfg_invalid = ExportData(
            config={},
            content="depth",
            name=name,
        ).export(regsurf)

    objpath_cfg_valid = ExportData(
        config=globalconfig1,
        content="depth",
        name=name,
    ).export(regsurf)

    assert Path(objpath_cfg_invalid) == tmp_path / f"share/results/maps/{name}.gri"
    assert Path(objpath_cfg_invalid).exists()
    assert Path(objpath_cfg_valid).exists()
    assert objpath_cfg_invalid == objpath_cfg_valid

    # test that it works with deprecated pattern also
    with pytest.warns(FutureWarning):
        objpath_cfg_valid = ExportData(config=globalconfig1).export(
            regsurf,
            content="depth",
            name=name,
        )
    assert objpath_cfg_invalid == objpath_cfg_valid


@pytest.mark.skip_inside_rmsvenv
def test_wrong_config_exports_correctly_in_fmu(
    monkeypatch, fmurun_w_casemetadata, globalconfig1, regsurf
):
    """
    In case a config is invalid, objects are exported without metadata.
    Test that the export path is correct and equal to exports with valid config,
    inside an fmu run.
    """

    # TODO: Refactor tests and move away from outside/inside rms pattern

    monkeypatch.chdir(fmurun_w_casemetadata)
    name = "mysurface"

    with pytest.warns(UserWarning, match="The global config"), pytest.warns(
        UserWarning, match="without metadata"
    ):
        objpath_cfg_invalid = ExportData(
            config={},
            content="depth",
            name=name,
        ).export(regsurf)

    objpath_cfg_valid = ExportData(
        config=globalconfig1,
        content="depth",
        name=name,
    ).export(regsurf)

    assert (
        Path(objpath_cfg_invalid)
        == fmurun_w_casemetadata / f"share/results/maps/{name}.gri"
    )
    assert Path(objpath_cfg_invalid).exists()
    assert Path(objpath_cfg_valid).exists()
    assert objpath_cfg_invalid == objpath_cfg_valid

    # test that it works with deprecated pattern also
    with pytest.warns(FutureWarning):
        objpath_cfg_valid = ExportData(config=globalconfig1).export(
            regsurf,
            content="depth",
            name=name,
        )
    assert objpath_cfg_invalid == objpath_cfg_valid


def test_config_miss_required_fields(monkeypatch, tmp_path, globalconfig1, regsurf):
    """Global config exists but missing critical data; export file but skip metadata."""

    monkeypatch.chdir(tmp_path)

    cfg = globalconfig1.copy()

    del cfg["access"]
    del cfg["masterdata"]
    del cfg["model"]

    with pytest.warns(UserWarning, match="The global config"):
        edata = ExportData(config=cfg, content="depth", name="mysurface")

    with pytest.warns(UserWarning):
        out = edata.export(regsurf)

    assert "mysurface" in out

    with pytest.raises(OSError, match="Cannot find requested metafile"):
        read_metadata(out)


def test_config_stratigraphy_alias_as_string(globalconfig2):
    """
    Test that 'alias' as string gives FutureWarning and is
    correctly converted to a list.
    """
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["alias"] = "TV"

    with pytest.warns(FutureWarning, match="string input"):
        exp = ExportData(config=cfg, content="depth", name="TopVolantis")

    assert exp.config
    assert exp.config.stratigraphy["TopVolantis"].alias == ["TV"]


def test_config_stratigraphy_empty_entries_alias(globalconfig2, regsurf):
    """Test that empty entries in 'alias' is detected and warned and removed."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["alias"] += [None]

    with pytest.warns(FutureWarning, match="empty list element"):
        exp = ExportData(config=cfg, content="depth", name="TopVolantis")
    metadata = exp.generate_metadata(regsurf)

    assert None not in metadata["data"]["alias"]


@pytest.mark.xfail(reason="stratigraphic_alias is not implemented")
def test_config_stratigraphy_empty_entries_stratigraphic_alias(globalconfig2, regsurf):
    """Test that empty entries in 'stratigraphic_alias' detected and warned."""

    # Note! stratigraphic_alias is not implemented, but we still check consistency

    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["stratigraphic_alias"] += [None]

    with pytest.warns(FutureWarning, match="empty list element"):
        exp = ExportData(config=cfg, content="depth")
    metadata = exp.generate_metadata(regsurf)

    assert None not in metadata["data"]["stratigraphic_alias"]


def test_config_stratigraphy_empty_name(globalconfig2):
    """Test that empty 'name' is detected and warned."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["name"] = None

    with pytest.warns(UserWarning, match="The global config"):
        ExportData(config=cfg, content="depth")


def test_config_stratigraphy_stratigraphic_not_bool(globalconfig2):
    """Test that non-boolean 'stratigraphic' is detected and warned."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["stratigraphic"] = None

    with pytest.warns(UserWarning, match="The global config"):
        ExportData(config=cfg, content="depth")

    cfg["stratigraphy"]["TopVolantis"]["stratigraphic"] = "a string"

    with pytest.warns(UserWarning, match="The global config"):
        ExportData(config=cfg, content="depth")


def test_update_check_settings_shall_fail(globalconfig1):
    # pylint: disable=unexpected-keyword-arg
    with pytest.raises(TypeError):
        _ = ExportData(config=globalconfig1, stupid="str", content="depth")

    newsettings = {"invalidkey": "some"}
    some = ExportData(config=globalconfig1, content="depth")
    with pytest.warns(FutureWarning), pytest.raises(KeyError):
        some._update_check_settings(newsettings)


@pytest.mark.skip_inside_rmsvenv
@pytest.mark.parametrize(
    "key, value, expected_msg",
    [
        (
            "runpath",
            "some",
            r"The 'runpath' key has currently no function",
        ),
        (
            "grid_model",
            "some",
            r"The 'grid_model' key has currently no function",
        ),
    ],
)
def test_deprecated_keys(globalconfig1, regsurf, key, value, expected_msg):
    """Some keys shall raise a DeprecationWarning or similar."""

    # TODO: Refactor tests and move away from outside/inside rms pattern

    # under primary initialisation
    kval = {key: value}
    with pytest.warns(UserWarning, match=expected_msg):
        ExportData(config=globalconfig1, content="depth", **kval)

    # under override should give FutureWarning for these
    edata = ExportData(config=globalconfig1, content="depth")
    with pytest.warns(UserWarning, match=expected_msg), pytest.warns(
        FutureWarning, match="move them up to initialization"
    ):
        edata.generate_metadata(regsurf, **kval)


def test_access_ssdl_vs_classification_rep_include(globalconfig1, regsurf):
    """
    The access_ssdl is deprecated, and replaced by the 'classification' and
    'rep_include' arguments. Test various combinations of these arguments.
    ."""

    # verify that a deprecation warning is given for access_ssdl argument
    with pytest.warns(FutureWarning, match="'access_ssdl' argument is deprecated"):
        exp = ExportData(
            config=globalconfig1,
            access_ssdl={"access_level": "restricted", "rep_include": True},
            content="depth",
        )
        mymeta = exp.generate_metadata(regsurf)
        assert mymeta["access"]["classification"] == "restricted"
        assert mymeta["access"]["ssdl"]["rep_include"] is True

    # 'access_ssdl' is not allowed together with any combination of
    # 'classification' / 'rep_include' arguments
    with pytest.warns(FutureWarning, match="deprecated"), pytest.raises(
        ValueError, match="is not supported"
    ):
        ExportData(
            access_ssdl={"access_level": "restricted"},
            classification="internal",
            content="depth",
        )
    with pytest.warns(FutureWarning, match="deprecated"), pytest.raises(
        ValueError, match="is not supported"
    ):
        ExportData(
            access_ssdl={"rep_include": True},
            rep_include=True,
            content="depth",
        )

    with pytest.warns(FutureWarning, match="deprecated"), pytest.raises(
        ValueError, match="is not supported"
    ):
        ExportData(
            access_ssdl={"access_level": "restricted"},
            rep_include=False,
            content="depth",
        )

    # using 'classification' / 'rep_include' as arguments is the preferred pattern
    exp = ExportData(
        config=globalconfig1,
        classification="restricted",
        rep_include=True,
        content="depth",
    )
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "restricted"
    assert mymeta["access"]["ssdl"]["rep_include"] is True


def test_classification(globalconfig1, regsurf):
    """Test that 'classification' is set correctly."""

    # test assumptions
    config = deepcopy(globalconfig1)
    assert config["access"]["classification"] == "internal"
    assert "ssdl" not in config["access"]

    # test that classification can be given directly and will override config
    exp = ExportData(config=config, classification="restricted", content="depth")
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "restricted"

    # test that classification can be given through deprecated access_ssdl
    with pytest.warns(FutureWarning, match="'access_ssdl' argument is deprecated"):
        exp = ExportData(
            config=config, access_ssdl={"access_level": "restricted"}, content="depth"
        )
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "restricted"

    # test that classification is taken from 'classification' in config if not provided
    exp = ExportData(config=config, content="depth")
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "internal"

    # test that classification is taken from access.ssdl.access_level
    # in config if classification is not present
    del config["access"]["classification"]
    config["access"]["ssdl"] = {"access_level": "restricted"}
    exp = ExportData(config=config, content="depth")
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "restricted"

    # verify that classification is defaulted to internal
    with pytest.warns(UserWarning):
        exp = ExportData(config={}, content="depth")
    with pytest.warns(FutureWarning):
        mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "internal"


def test_rep_include(globalconfig1, regsurf):
    """Test that 'classification' is set correctly."""

    # test assumptions
    assert "ssdl" not in globalconfig1["access"]  # means no rep_include

    # test that rep_include can be given directly and will override config
    exp = ExportData(config=globalconfig1, rep_include=True, content="depth")
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["ssdl"]["rep_include"] is True

    # test that rep_include can be given through access_ssdl
    with pytest.warns(FutureWarning, match="'access_ssdl' argument is deprecated"):
        exp = ExportData(
            config=globalconfig1, access_ssdl={"rep_include": True}, content="depth"
        )
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["ssdl"]["rep_include"] is True

    # test that rep_include is defaulted to false if not provided
    exp = ExportData(config=globalconfig1, content="depth")
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["ssdl"]["rep_include"] is False

    # add ssdl.rep_include to the config
    config = deepcopy(globalconfig1)
    config["access"]["ssdl"] = {"rep_include": True}

    # test that rep_include can be read from config
    with pytest.warns(FutureWarning, match="is deprecated"):
        mymeta = ExportData(config=config, content="depth").generate_metadata(regsurf)
    assert mymeta["access"]["ssdl"]["rep_include"] is True


def test_unit_is_none(globalconfig1, regsurf):
    """Test that unit=None works and is translated into an enpty string"""
    eobj = ExportData(config=globalconfig1, unit=None, content="depth")
    meta = eobj.generate_metadata(regsurf)
    assert meta["data"]["unit"] == ""


def test_content_not_given(globalconfig1, regsurf):
    """When content is not explicitly given, warning shall be issued."""
    eobj = ExportData(config=globalconfig1)
    with pytest.warns(FutureWarning, match="The <content> is not provided"):
        mymeta = eobj.generate_metadata(regsurf)

    assert mymeta["data"]["content"] == "unset"


def test_content_given_init_or_later(globalconfig1, regsurf):
    """When content is not explicitly given, warning shall be issued."""
    eobj = ExportData(config=globalconfig1, content="time")
    mymeta = eobj.generate_metadata(regsurf)

    assert mymeta["data"]["content"] == "time"

    # override by adding content at generate_metadata
    with pytest.warns(FutureWarning, match="move them up to initialization"):
        mymeta = eobj.generate_metadata(regsurf, content="depth")

    assert mymeta["data"]["content"] == "depth"  # last content shall win


def test_content_invalid_string(globalconfig1, regsurf):
    eobj = ExportData(config=globalconfig1, content="not_valid")
    with pytest.raises(ValueError, match="Invalid 'content' value='not_valid'"):
        eobj.generate_metadata(regsurf)


def test_content_invalid_dict(globalconfig1, regsurf):
    eobj = ExportData(
        config=globalconfig1, content={"not_valid": {"some_key": "some_value"}}
    )
    with pytest.raises(ValueError, match="Invalid 'content' value='not_valid'"):
        eobj.generate_metadata(regsurf)

    eobj = ExportData(
        config=globalconfig1, content={"seismic": "some_key", "extra": "some_value"}
    )
    with pytest.raises(ValueError):
        eobj.generate_metadata(regsurf)


def test_content_metadata_valid(globalconfig1, regsurf):
    content_metadata = {"attribute": "amplitude", "calculation": "mean"}
    meta = ExportData(
        config=globalconfig1,
        content="seismic",
        content_metadata=content_metadata,
    ).generate_metadata(regsurf)

    assert meta["data"]["content"] == "seismic"
    assert "seismic" in meta["data"]
    assert meta["data"]["seismic"] == content_metadata


def test_content_metadata_invalid(globalconfig1, regsurf):
    with pytest.raises(pydantic.ValidationError):
        ExportData(
            config=globalconfig1,
            content="seismic",
            content_metadata={"attribute": 182},
        ).generate_metadata(regsurf)


def test_content_valid_string(regsurf, globalconfig2):
    eobj = ExportData(config=globalconfig2, name="TopVolantis", content="depth")
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["content"] == "depth"
    assert "depth" not in mymeta["data"]


def test_seismic_content_require_seismic_data(globalconfig2, regsurf):
    eobj = ExportData(config=globalconfig2, content="seismic")
    with pytest.raises(ValueError, match="requires additional input"):
        eobj.generate_metadata(regsurf)


def test_content_valid_dict(regsurf, globalconfig2):
    """Test for incorrectly formatted dict.

    When a dict is given, there shall be one key which is the content, and there shall
    be one value, which shall be a dictionary containing content-specific attributes."""

    eobj = ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content={
            "seismic": {
                "attribute": "amplitude",
                "calculation": "mean",
                "zrange": 12.0,
                "stacking_offset": "0-15",
            }
        },
    )
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["content"] == "seismic"
    assert mymeta["data"]["seismic"] == {
        "attribute": "amplitude",
        "calculation": "mean",
        "zrange": 12.0,
        "stacking_offset": "0-15",
    }


def test_content_is_a_wrongly_formatted_dict(globalconfig2, regsurf):
    """When content is a dict, it shall have one key with one dict as value."""
    eobj = ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content={"seismic": "myvalue"},
    )
    with pytest.raises(ValueError):
        eobj.generate_metadata(regsurf)


def test_content_is_dict_with_wrong_types(globalconfig2, regsurf):
    """When content is a dict, it shall have right types for known keys."""
    eobj = ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content={
            "seismic": {
                "stacking_offset": 123.4,  # not a string
            }
        },
    )
    with pytest.raises(pydantic.ValidationError):
        eobj.generate_metadata(regsurf)


def test_content_with_content_metadata(globalconfig2, polygons):
    """When content_metadata is given and allowed, it shall be produced to metadata."""
    eobj = ExportData(
        config=globalconfig2,
        name="Central Horst",
        content="field_region",
        content_metadata={"id": 1},
    )
    mymeta = eobj.generate_metadata(polygons)

    assert mymeta["data"]["name"] == "Central Horst"
    assert mymeta["data"]["content"] == "field_region"
    assert "field_region" in mymeta["data"]
    assert mymeta["data"]["field_region"] == {"id": 1}


def test_content_deprecated_seismic_offset(regsurf, globalconfig2):
    """Assert that usage of seismic.offset still works but give deprecation warning."""
    with pytest.warns(DeprecationWarning, match="seismic.offset is deprecated"):
        eobj = ExportData(
            config=globalconfig2,
            name="TopVolantis",
            content={
                "seismic": {
                    "offset": "0-15",
                }
            },
        )
        mymeta = eobj.generate_metadata(regsurf)

    # deprecated 'offset' replaced with 'stacking_offset'
    assert "offset" not in mymeta["data"]["seismic"]
    assert mymeta["data"]["seismic"] == {
        "stacking_offset": "0-15",
    }


def test_content_metdata_ignored(globalconfig1, regsurf):
    """Test that warning is given when content does not require content_metadata"""
    with pytest.warns(UserWarning, match="ignoring input"):
        ExportData(
            config=globalconfig1,
            content="depth",
            content_metadata={"extra": "invalid"},
        ).generate_metadata(regsurf)


@pytest.mark.filterwarnings("ignore: Number of maps nodes are 0")
def test_surfaces_with_non_finite_values(
    globalconfig1, regsurf_masked_only, regsurf_nan_only, regsurf
):
    """
    When a surface has no finite values the zmin/zmax should not be present
    in the metadata.
    """

    eobj = ExportData(config=globalconfig1, content="time")

    # test surface with only masked values
    mymeta = eobj.generate_metadata(regsurf_masked_only)
    assert "zmin" not in mymeta["data"]["bbox"]
    assert "zmax" not in mymeta["data"]["bbox"]

    # test surface with only nan values
    mymeta = eobj.generate_metadata(regsurf_nan_only)
    assert "zmin" not in mymeta["data"]["bbox"]
    assert "zmax" not in mymeta["data"]["bbox"]

    # test surface with finite values has zmin/zmax
    mymeta = eobj.generate_metadata(regsurf)
    assert "zmin" in mymeta["data"]["bbox"]
    assert "zmax" in mymeta["data"]["bbox"]


def test_workflow_as_string(fmurun_w_casemetadata, monkeypatch, globalconfig1, regsurf):
    """
    Check that having workflow as string works both in ExportData and on export.
    The workflow string input is given into the metadata as fmu.workflow.reference
    """

    monkeypatch.chdir(fmurun_w_casemetadata)

    workflow = "My test workflow"

    # check that it works in ExportData
    edata = ExportData(config=globalconfig1, workflow=workflow, content="depth")
    meta = edata.generate_metadata(regsurf)
    assert meta["fmu"]["workflow"]["reference"] == workflow

    # doing actual export with a few ovverides
    edata = ExportData(config=globalconfig1, content="depth")
    with pytest.warns(FutureWarning, match="move them up to initialization"):
        meta = edata.generate_metadata(regsurf, workflow="My test workflow")
    assert meta["fmu"]["workflow"]["reference"] == workflow


def test_vertical_domain(regsurf, globalconfig1):
    """test inputting vertical_domain and domain_reference in various ways"""

    # test that giving vertical_domain and domain_reference as strings
    mymeta = ExportData(
        config=globalconfig1,
        vertical_domain="time",
        domain_reference="rkb",
        content="time",
    ).generate_metadata(regsurf)
    assert mymeta["data"]["vertical_domain"] == "time"
    assert mymeta["data"]["domain_reference"] == "rkb"

    # test giving vertical_domain as dictionary
    with pytest.warns(FutureWarning, match="deprecated"):
        mymeta = ExportData(
            config=globalconfig1, vertical_domain={"time": "sb"}, content="thickness"
        ).generate_metadata(regsurf)
    assert mymeta["data"]["vertical_domain"] == "time"
    assert mymeta["data"]["domain_reference"] == "sb"

    # test excluding vertical_domain and domain_reference
    mymeta = ExportData(config=globalconfig1, content="thickness").generate_metadata(
        regsurf
    )
    assert mymeta["data"]["vertical_domain"] == "depth"  # default value
    assert mymeta["data"]["domain_reference"] == "msl"  # default value

    # test invalid input
    with pytest.raises(pydantic.ValidationError, match="vertical_domain"):
        ExportData(
            config=globalconfig1, vertical_domain="wrong", content="thickness"
        ).generate_metadata(regsurf)
    with pytest.raises(pydantic.ValidationError, match="domain_reference"):
        ExportData(
            config=globalconfig1, domain_reference="wrong", content="thickness"
        ).generate_metadata(regsurf)
    with pytest.warns(FutureWarning, match="deprecated"), pytest.raises(
        pydantic.ValidationError, match="2 validation errors"
    ):
        ExportData(
            config=globalconfig1, vertical_domain={"invalid": 5}, content="thickness"
        ).generate_metadata(regsurf)


def test_vertical_domain_vs_depth_time_content(regsurf, globalconfig1):
    """Test the vertical_domain vs content depth/time"""

    # test content depth/time sets vertical_domain
    eobj = ExportData(config=globalconfig1, content="depth")
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["vertical_domain"] == "depth"
    assert mymeta["data"]["domain_reference"] == "msl"  # default value

    eobj = ExportData(config=globalconfig1, content="depth", domain_reference="sb")
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["vertical_domain"] == "depth"
    assert mymeta["data"]["domain_reference"] == "sb"

    eobj = ExportData(config=globalconfig1, content="time")
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["vertical_domain"] == "time"
    assert mymeta["data"]["domain_reference"] == "msl"  # default value

    # test mismatch between content and vertical_domain
    with pytest.warns(UserWarning, match="'vertical_domain' will be set to 'depth'"):
        eobj = ExportData(config=globalconfig1, content="depth", vertical_domain="time")
        mymeta = eobj.generate_metadata(regsurf)

    with pytest.warns(UserWarning, match="'vertical_domain' will be set to 'time'"):
        eobj = ExportData(config=globalconfig1, content="time", vertical_domain="depth")
        mymeta = eobj.generate_metadata(regsurf)


def test_set_display_name(regsurf, globalconfig2):
    """Test that giving the display_name argument sets display.name."""
    eobj = ExportData(
        config=globalconfig2,
        name="MyName",
        display_name="MyDisplayName",
        content="depth",
    )
    mymeta = eobj.generate_metadata(regsurf)

    assert mymeta["data"]["name"] == "MyName"
    assert mymeta["display"]["name"] == "MyDisplayName"

    # also test when setting directly in the method call (not allowed in the future)
    with pytest.warns(FutureWarning, match="move them up to initialization"):
        mymeta = eobj.generate_metadata(regsurf, display_name="MyOtherDisplayName")

    assert mymeta["data"]["name"] == "MyName"
    assert mymeta["display"]["name"] == "MyOtherDisplayName"


def test_global_config_from_env(monkeypatch, global_config2_path, globalconfig1):
    """Testing getting global config from a file"""
    monkeypatch.setenv("FMU_GLOBAL_CONFIG", str(global_config2_path))

    edata = ExportData(content="depth")  # the env variable will override this
    assert edata.config.masterdata.smda
    assert edata.config.model.name == "ff"

    # do not use global config from environment when explicitly given
    edata = ExportData(config=globalconfig1, content="depth")
    assert edata.config.model.name == "Test"


def test_fmurun_attribute_outside_fmu(rmsglobalconfig):
    """Test that _fmurun attribute is True when in fmu"""

    # check that ERT environment variable is not set
    assert FmuEnv.ENSEMBLE_ID.value is None

    edata = ExportData(config=rmsglobalconfig, content="depth")
    assert edata._fmurun is False


def test_exportdata_no_iter_folder(
    fmurun_no_iter_folder, rmsglobalconfig, regsurf, monkeypatch
):
    """Test that the fmuprovider works without a iteration folder"""

    monkeypatch.chdir(fmurun_no_iter_folder)
    edata = ExportData(config=rmsglobalconfig, content="depth")
    assert edata._fmurun is True

    out = Path(edata.export(regsurf))
    with open(out.parent / f".{out.name}.yml", encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    assert metadata["fmu"]["realization"]["name"] == "realization-1"
    assert metadata["fmu"]["realization"]["id"] == 1
    assert metadata["fmu"]["iteration"]["name"] == "iter-0"
    assert metadata["fmu"]["iteration"]["id"] == 0


def test_fmucontext_case_casepath(fmurun_prehook, rmsglobalconfig, regsurf):
    """
    Test fmu_context case when casepath is / is not explicitly given

    In the future we would like to not be able to update casepath outside
    of initialization, but it needs to be deprecated first.
    """
    assert FmuEnv.RUNPATH.value is None
    assert FmuEnv.EXPERIMENT_ID.value is not None
    assert FmuEnv.SIMULATION_MODE.value is not None

    # will give warning when casepath not provided
    with pytest.warns(UserWarning, match="Could not auto detect"):
        edata = ExportData(config=rmsglobalconfig, content="depth")

    # should still give warning when casepath not provided and create empty fmu metadata
    with pytest.warns(UserWarning, match="Could not auto detect"):
        meta = edata.generate_metadata(regsurf)
    assert "fmu" not in meta

    # no warning when casepath is provided and metadata is valid
    # should however issue a warning to move it to initialization
    with pytest.warns(FutureWarning, match="move them up to initialization"):
        meta = edata.generate_metadata(regsurf, casepath=fmurun_prehook)
    assert "fmu" in meta
    assert meta["fmu"]["case"]["name"] == "somecasename"


def test_fmurun_attribute_inside_fmu(fmurun_w_casemetadata, rmsglobalconfig):
    """Test that _fmurun attribute is True when in fmu"""

    # check that ERT environment variable is not set
    assert FmuEnv.ENSEMBLE_ID.value is not None
    assert FmuEnv.SIMULATION_MODE.value is not None

    edata = ExportData(config=rmsglobalconfig, content="depth")
    assert edata._fmurun is True


def test_fmu_context_not_given_fetch_from_env_realization(
    fmurun_w_casemetadata, rmsglobalconfig
):
    """
    Test fmu_context not explicitly given, should be set to "realization" when
    inside fmu and RUNPATH value is detected from the environment variables.
    """
    assert FmuEnv.RUNPATH.value is not None
    assert FmuEnv.SIMULATION_MODE.value is not None
    assert FmuEnv.EXPERIMENT_ID.value is not None

    edata = ExportData(config=rmsglobalconfig, content="depth")
    assert edata._fmurun is True
    assert edata.fmu_context == FMUContext.realization


def test_fmu_context_not_given_fetch_from_env_case(fmurun_prehook, rmsglobalconfig):
    """
    Test fmu_context not explicitly given, should be set to "case" when
    inside fmu and RUNPATH value not detected from the environment variables.
    """
    assert FmuEnv.RUNPATH.value is None
    assert FmuEnv.SIMULATION_MODE.value is not None
    assert FmuEnv.EXPERIMENT_ID.value is not None

    # will give warning when casepath not provided
    with pytest.warns(UserWarning, match="Could not auto detect"):
        edata = ExportData(config=rmsglobalconfig, content="depth")

    # test that it runs properly when casepath is provided
    edata = ExportData(config=rmsglobalconfig, content="depth", casepath=fmurun_prehook)
    assert edata._fmurun is True
    assert edata.fmu_context == FMUContext.case
    assert edata._rootpath == fmurun_prehook


def test_fmu_context_not_given_fetch_from_env_nonfmu(rmsglobalconfig):
    """
    Test fmu_context not explicitly given, should be set to None when
    outside fmu.
    """
    assert FmuEnv.RUNPATH.value is None
    assert FmuEnv.EXPERIMENT_ID.value is None
    assert FmuEnv.SIMULATION_MODE.value is None

    edata = ExportData(config=rmsglobalconfig, content="depth")
    assert edata._fmurun is False
    assert edata.fmu_context is None


def test_fmu_context_outside_fmu_input_overwrite(rmsglobalconfig):
    """
    For non-fmu run fmu_context should be overwritten to None when input
    is not "preprocessed"
    """
    edata = ExportData(
        config=rmsglobalconfig, content="depth", fmu_context="realization"
    )
    assert edata._fmurun is False
    assert edata.fmu_context is None


def test_fmu_context_outside_fmu_no_input_overwrite(rmsglobalconfig):
    """
    For non-fmu run fmu_context should not be overwritten when input
    is "preprocessed"
    """
    edata = ExportData(config=rmsglobalconfig, content="depth", preprocessed=True)
    assert edata._fmurun is False
    assert edata.preprocessed is True
    assert edata.fmu_context is None


def test_fmu_context_preprocessed_deprecation_outside_fmu(rmsglobalconfig, regsurf):
    """
    Test the deprecated fmu_context="preprocessed" outside fmu.
    This should set the preprocessed flag to True and overwrite the
    fmu_context (if any) to "non-fmu".
    """
    with pytest.warns(FutureWarning, match="is deprecated"):
        edata = ExportData(
            config=rmsglobalconfig, content="depth", fmu_context="preprocessed"
        )
    assert edata.preprocessed is True
    assert edata.fmu_context is None

    meta = edata.generate_metadata(regsurf)
    assert meta["file"]["relative_path"] == "share/preprocessed/maps/unknown.gri"


def test_fmu_context_preprocessed_deprecation_inside_fmu(
    fmurun_prehook, rmsglobalconfig, regsurf
):
    """
    Test the deprecated fmu_context="preprocessed" inside fmu.
    This should set the preprocessed flag to True and overwrite the
    fmu_context (if any) to "case".
    """
    with pytest.warns(FutureWarning, match="is deprecated"):
        edata = ExportData(
            config=rmsglobalconfig,
            content="depth",
            fmu_context="preprocessed",
            casepath=fmurun_prehook,
        )
    assert edata.preprocessed is True
    assert edata.fmu_context == FMUContext.case

    meta = edata.generate_metadata(regsurf)
    assert meta["file"]["relative_path"] == "share/preprocessed/maps/unknown.gri"


def test_preprocessed_outside_fmu(rmsglobalconfig, regsurf):
    """Test the preprocessed argument outside FMU context"""

    edata = ExportData(config=rmsglobalconfig, content="depth", preprocessed=True)
    assert edata.preprocessed is True
    assert edata.fmu_context is None

    meta = edata.generate_metadata(regsurf)
    # check that the relative file is at case level and has a preprocessed folder
    assert meta["file"]["relative_path"] == "share/preprocessed/maps/unknown.gri"


def test_preprocessed_inside_fmu(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test the preprocessed argument inside FMU context"""
    # should raise error if preprocessed=True and fmu_context="realization"
    with pytest.raises(ValueError, match="Can't export preprocessed"):
        edata = ExportData(
            config=rmsglobalconfig,
            content="depth",
            fmu_context="realization",
            preprocessed=True,
        )

    # test that no error is raised if preprocessed=True and fmu_context="case"
    edata = ExportData(
        config=rmsglobalconfig,
        content="depth",
        fmu_context="case",
        preprocessed=True,
    )
    assert edata._fmurun is True
    assert edata.preprocessed is True
    assert edata.fmu_context == FMUContext.case

    meta = edata.generate_metadata(regsurf)
    # check that the relative file is at case level and has a preprocessed folder
    assert meta["file"]["relative_path"] == "share/preprocessed/maps/unknown.gri"


def test_norwegian_letters_globalconfig(
    globalvars_norwegian_letters,
    regsurf,
    monkeypatch,
):
    """Testing using norwegian letters in global config.

    Note that fmu.config utilities yaml_load() is applied to read cfg (cf conftest.py)
    """

    path, cfg, cfg_asfile = globalvars_norwegian_letters

    os.chdir(path)

    edata = ExportData(content="depth", config=cfg, name="TopBlåbær")
    meta = edata.generate_metadata(regsurf)
    logger.debug("\n %s", prettyprint_dict(meta))
    assert meta["data"]["name"] == "TopBlåbær"
    assert meta["masterdata"]["smda"]["field"][0]["identifier"] == "DRÅGØN"

    # export to file and reread as raw
    result = pathlib.Path(edata.export(regsurf))
    metafile = result.parent / ("." + str(result.stem) + ".gri.yml")
    with open(metafile, encoding="utf-8") as stream:
        assert "DRÅGØN" in stream.read()

    # read file as global config

    monkeypatch.setenv("FMU_GLOBAL_CONFIG", cfg_asfile)
    edata2 = ExportData(
        content="depth", name="TopBlåbær"
    )  # the env variable will override this
    meta2 = edata2.generate_metadata(regsurf)
    logger.debug("\n %s", prettyprint_dict(meta2))
    assert meta2["data"]["name"] == "TopBlåbær"
    assert meta2["masterdata"]["smda"]["field"][0]["identifier"] == "DRÅGØN"


def test_metadata_format_deprecated(globalconfig1, regsurf, tmp_path, monkeypatch):
    """
    Test that setting the class variable "metadata_format" gives a warning,
    and that writing metadata on json format does not work
    """
    monkeypatch.chdir(tmp_path)

    ExportData.meta_format = "json"
    with pytest.warns(UserWarning, match="meta_format"):
        result = ExportData(
            config=globalconfig1, name="TopBlåbær", content="depth"
        ).export(regsurf)

    result = pathlib.Path(result)
    metafile = result.parent / ("." + str(result.stem) + ".gri.json")
    assert not metafile.exists()
    assert not metafile.with_suffix(".yaml").exists()

    # test that also value "yaml" will cause warning
    ExportData.meta_format = "yaml"
    with pytest.warns(UserWarning, match="meta_format"):
        ExportData(config=globalconfig1, name="TopBlåbær", content="depth")

    ExportData.meta_format = None  # reset


def test_establish_runpath(tmp_path, globalconfig2):
    """Testing pwd and rootpath from RMS"""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    edata = ExportData(config=globalconfig2, content="depth")
    edata._establish_rootpath()

    assert edata._rootpath == rmspath.parent.parent

    ExportData._inside_rms = False  # reset


@pytest.mark.skipif("win" in sys.platform, reason="Windows tests have no /tmp")
def test_forcefolder(tmp_path, globalconfig2, regsurf):
    """Testing the forcefolder mechanism."""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    edata = ExportData(config=globalconfig2, content="depth", forcefolder="whatever")
    meta = edata.generate_metadata(regsurf)
    logger.info("RMS PATH %s", rmspath)
    logger.info("\n %s", prettyprint_dict(meta))
    assert meta["file"]["relative_path"].startswith("share/results/whatever/")
    ExportData._inside_rms = False  # reset


@pytest.mark.skipif("win" in sys.platform, reason="Windows tests have no /tmp")
def test_forcefolder_absolute_shall_raise_or_warn(tmp_path, globalconfig2, regsurf):
    """Testing the forcefolder mechanism."""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    ExportData.allow_forcefolder_absolute = False

    edata = ExportData(
        config=globalconfig2, content="depth", forcefolder="/tmp/what", name="x"
    )
    with pytest.raises(ValueError, match="Can't use absolute path as 'forcefolder'"):
        edata.generate_metadata(regsurf)

    with pytest.warns(UserWarning, match="is deprecated"):
        ExportData.allow_forcefolder_absolute = True
        ExportData(config=globalconfig2, content="depth", forcefolder="/tmp/what")

    ExportData._inside_rms = False
    ExportData.allow_forcefolder_absolute = False


def test_deprecated_verbosity(globalconfig1):
    with pytest.warns(UserWarning, match="Using the 'verbosity' key is now deprecated"):
        ExportData(config=globalconfig1, verbosity="INFO")


@pytest.mark.parametrize("encoding", ("utf-8", "latin1"))
@pytest.mark.parametrize("mode", ("w", "w+"))
def test_norwegian_letters(encoding, mode, tmp_path):
    with open(tmp_path / "no-letters.yml", encoding=encoding, mode=mode) as f:
        f.write(
            """æøå:
  æøå"""
        )

    with open(tmp_path / "no-letters.yml", encoding=encoding) as f:
        assert yaml.safe_load(f) == {"æøå": "æøå"}


def test_content_seismic_as_string_validation_error(globalconfig2, regsurf):
    edata = ExportData(content="seismic", config=globalconfig2)
    with pytest.raises(ValueError, match="requires additional input"):
        edata.generate_metadata(regsurf)

    # correct way, should not fail
    edata = ExportData(
        content="seismic",
        content_metadata={"attribute": "attribute-value"},
        config=globalconfig2,
    )
    meta = edata.generate_metadata(regsurf)
    assert meta["data"]["content"] == "seismic"
    assert meta["data"]["seismic"] == {"attribute": "attribute-value"}


def test_content_property_as_string_future_warning(globalconfig2, regsurf):
    edata = ExportData(content="property", config=globalconfig2)
    with pytest.warns(FutureWarning):
        edata.generate_metadata(regsurf)


def test_append_to_alias_list(globalconfig2, regsurf):
    """
    Test that the name input is added to the alias list when present in
    the stratigraphy. And check that the alias list is not appended to if it
    contains the name already.
    """

    name = "TopVolantis"
    strat = globalconfig2["stratigraphy"][name]
    assert name not in strat["alias"]

    # generate metadata twice on the same ExportData instance
    # to check that the alias list is not appended the second time
    edata = ExportData(content="depth", config=globalconfig2, name=name)
    meta = edata.generate_metadata(regsurf)
    meta2 = edata.generate_metadata(regsurf)

    assert meta["data"]["alias"] == meta2["data"]["alias"]

    # also check that the name input was added to the alias list
    assert name not in strat["alias"]
    assert name in meta["data"]["alias"]


def test_alias_as_none(globalconfig2, regsurf):
    """Test that 'alias: None' in the config works"""

    config = deepcopy(globalconfig2)
    name = "TopVolantis"
    config["stratigraphy"][name]["alias"] = None

    edata = ExportData(content="depth", config=config, name=name)
    meta = edata.generate_metadata(regsurf)

    assert meta["data"]["name"] == "VOLANTIS GP. Top"
    assert meta["data"]["alias"] == [name]


def test_standard_result_not_present_in_generated_metadata(globalconfig1, regsurf):
    """Test that data.standard_result is not set for regular exports through
    ExportData"""

    meta = ExportData(config=globalconfig1, content="depth").generate_metadata(regsurf)
    assert "standard_result" not in meta["data"]


def test_ert_experiment_id_present_in_generated_metadata(
    fmurun_w_casemetadata, monkeypatch, globalconfig1, regsurf
):
    """Test that the ert experiment id has been set correctly
    in the generated metadata"""

    monkeypatch.chdir(fmurun_w_casemetadata)

    edata = ExportData(config=globalconfig1, content="depth")
    meta = edata.generate_metadata(regsurf)
    expected_id = "6a8e1e0f-9315-46bb-9648-8de87151f4c7"
    assert meta["fmu"]["ert"]["experiment"]["id"] == expected_id


def test_ert_experiment_id_present_in_exported_metadata(
    fmurun_w_casemetadata, monkeypatch, globalconfig1, regsurf
):
    """Test that the ert experiment id has been set correctly
    in the exported metadata"""

    monkeypatch.chdir(fmurun_w_casemetadata)

    edata = ExportData(config=globalconfig1, content="depth")
    out = Path(edata.export(regsurf))
    with open(out.parent / f".{out.name}.yml", encoding="utf-8") as f:
        export_meta = yaml.safe_load(f)
    expected_id = "6a8e1e0f-9315-46bb-9648-8de87151f4c7"
    assert export_meta["fmu"]["ert"]["experiment"]["id"] == expected_id


def test_ert_simulation_mode_present_in_generated_metadata(
    fmurun_w_casemetadata, monkeypatch, globalconfig1, regsurf
):
    """Test that the ert simulation mode has been set correctly
    in the generated metadata"""

    monkeypatch.chdir(fmurun_w_casemetadata)

    edata = ExportData(config=globalconfig1, content="depth")
    meta = edata.generate_metadata(regsurf)
    assert meta["fmu"]["ert"]["simulation_mode"] == "test_run"


def test_ert_simulation_mode_present_in_exported_metadata(
    fmurun_w_casemetadata, monkeypatch, globalconfig1, regsurf
):
    """Test that the ert simulation mode has been set correctly
    in the exported metadata"""

    monkeypatch.chdir(fmurun_w_casemetadata)

    edata = ExportData(config=globalconfig1, content="depth")
    out = Path(edata.export(regsurf))
    with open(out.parent / f".{out.name}.yml", encoding="utf-8") as f:
        export_meta = yaml.safe_load(f)
    assert export_meta["fmu"]["ert"]["simulation_mode"] == "test_run"


def test_offset_top_base_present_in_exported_metadata(globalconfig1, regsurf):
    """
    Test that top, base and offset information provided from the config are
    preserved in the exported metadata.
    """
    config = deepcopy(globalconfig1)
    name = "TopWhatever"

    # the globalconfig1 does not have this information so add it
    config["stratigraphy"][name].update(
        {
            "top": {"name": "TheTopHorizon"},
            "base": {"name": "TheBaseHorizon"},
            "offset": 3.5,
        }
    )
    edata = ExportData(config=config, content="depth", name=name)

    # check that it is preserved after initialization with pydantic
    assert edata.config.stratigraphy[name].top.name == "TheTopHorizon"
    assert edata.config.stratigraphy[name].base.name == "TheBaseHorizon"
    assert edata.config.stratigraphy[name].offset == 3.5

    # check that it is preserved in the generated metadata
    meta = edata.generate_metadata(regsurf)
    assert meta["data"]["offset"] == 3.5
    assert meta["data"]["top"]["name"] == "TheTopHorizon"
    assert meta["data"]["base"]["name"] == "TheBaseHorizon"


def test_top_base_as_strings_from_config(globalconfig1, regsurf):
    """
    Test that entering top, base as string is allowed and it sets
    the name attribute automatically.
    """
    config = deepcopy(globalconfig1)
    name = "TopWhatever"

    # add top and base info as string input to the config
    config["stratigraphy"][name].update(
        {
            "top": "TheTopHorizon",
            "base": "TheBaseHorizon",
        }
    )
    edata = ExportData(config=config, content="depth", name=name)

    # check that the name attribute for top/base is set correctly
    meta = edata.generate_metadata(regsurf)
    assert meta["data"]["top"]["name"] == "TheTopHorizon"
    assert meta["data"]["base"]["name"] == "TheBaseHorizon"


def test_timedata_single_date(globalconfig1, regsurf):
    """Test that entering a single date works"""

    t0 = "20230101"

    meta = ExportData(
        config=globalconfig1,
        content="depth",
        name="TopWhatever",
        timedata=[t0],
    ).generate_metadata(regsurf)

    assert meta["data"]["time"]["t0"]["value"] == convert_datestr_to_isoformat(t0)
    assert "t1" not in meta["data"]["time"]

    # should also work with the double list syntax
    meta = ExportData(
        config=globalconfig1,
        content="depth",
        name="TopWhatever",
        timedata=[[t0]],
    ).generate_metadata(regsurf)

    assert meta["data"]["time"]["t0"]["value"] == convert_datestr_to_isoformat(t0)
    assert "t1" not in meta["data"]["time"]


def test_timedata_multiple_date(globalconfig1, regsurf):
    """Test that entering two dates works"""

    t0 = "20230101"
    t1 = "20240101"

    meta = ExportData(
        config=globalconfig1,
        content="depth",
        name="TopWhatever",
        timedata=[t0, t1],
    ).generate_metadata(regsurf)

    assert meta["data"]["time"]["t0"]["value"] == convert_datestr_to_isoformat(t0)
    assert meta["data"]["time"]["t1"]["value"] == convert_datestr_to_isoformat(t1)

    # should also work with the double list syntax
    meta = ExportData(
        config=globalconfig1,
        content="depth",
        name="TopWhatever",
        timedata=[[t0], [t1]],
    ).generate_metadata(regsurf)

    assert meta["data"]["time"]["t0"]["value"] == convert_datestr_to_isoformat(t0)
    assert meta["data"]["time"]["t1"]["value"] == convert_datestr_to_isoformat(t1)


def test_timedata_multiple_date_sorting(globalconfig1, regsurf):
    """Test that dates are sorted no matter the input order"""

    t0 = "20230101"
    t1 = "20240101"

    meta = ExportData(
        config=globalconfig1,
        content="depth",
        name="TopWhatever",
        timedata=[t1, t0],  # set oldest first
    ).generate_metadata(regsurf)

    # check that oldest is t0
    assert meta["data"]["time"]["t0"]["value"] == convert_datestr_to_isoformat(t0)
    assert meta["data"]["time"]["t1"]["value"] == convert_datestr_to_isoformat(t1)


def test_timedata_wrong_format(globalconfig1, regsurf):
    """Test that error is raised if timedata is input incorrect"""

    with pytest.raises(ValueError, match="should be a list"):
        ExportData(
            config=globalconfig1,
            content="depth",
            name="TopWhatever",
            timedata="20230101",
        ).generate_metadata(regsurf)

    with pytest.raises(ValueError, match="two dates"):
        ExportData(
            config=globalconfig1,
            content="depth",
            name="TopWhatever",
            timedata=["20230101", "20240101", "20250101"],
        ).generate_metadata(regsurf)


def test_export_with_standard_result_valid_config(
    fmurun_w_casemetadata, monkeypatch, globalconfig1, mock_volumes
):
    """Test that standard result is set in metadata when
    export_with_standard_result is used"""
    monkeypatch.chdir(fmurun_w_casemetadata)

    edata = ExportData(
        config=globalconfig1,
        content="volumes",
        name="TopWhatever",
    )
    # for a regular export 'standard_result' should not be set
    outpath = edata.export(mock_volumes)
    meta = read_metadata(outpath)
    assert "standard_result" not in meta["data"]

    # when using export_with_standard_result 'standard_result' should be set
    outpath = edata._export_with_standard_result(
        mock_volumes,
        standard_result=InplaceVolumesStandardResult(
            name=StandardResultName.inplace_volumes
        ),
    )
    meta = read_metadata(outpath)
    assert (
        meta["data"]["standard_result"]["name"]
        == StandardResultName.inplace_volumes.value
    )


def test_export_with_standard_result_invalid_config(mock_volumes):
    """Test that error is raised if config is invalid"""
    with pytest.warns(UserWarning):
        edata = ExportData(
            config={},
            content="volumes",
            name="TopWhatever",
        )
    with pytest.raises(ValueError, match="config"):
        edata._export_with_standard_result(
            mock_volumes,
            standard_result=InplaceVolumesStandardResult(
                name=StandardResultName.inplace_volumes
            ),
        )
