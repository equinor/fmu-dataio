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
from fmu.dataio._definitions import FmuContext
from fmu.dataio._utils import prettyprint_dict
from fmu.dataio.dataio import ExportData, read_metadata
from fmu.dataio.providers._fmu import FmuEnv

# pylint: disable=no-member

logger = logging.getLogger(__name__)


def pydantic_warning() -> str:
    return r"""The global configuration has one or more errors that makes it
impossible to create valid metadata. The data will still be exported but no
metadata will be made. You are strongly encouraged to correct your
configuration. Invalid configuration may be disallowed in future versions.

Detailed information:
\d+ validation error(s)? for GlobalConfiguration
"""


def test_generate_metadata_simple(globalconfig1):
    """Test generating metadata"""

    default_fformat = ExportData.grid_fformat
    ExportData.grid_fformat = "grdecl"

    logger.info("Config in: \n%s", globalconfig1)

    edata = ExportData(config=globalconfig1, content="depth")

    assert edata.config["model"]["name"] == "Test"

    assert edata.meta_format == "yaml"
    assert edata.grid_fformat == "grdecl"
    assert edata.name == ""

    ExportData.grid_fformat = default_fformat  # reset


def test_missing_or_wrong_config_exports_with_warning(monkeypatch, tmp_path, regsurf):
    """In case a config is missing, or is invalid, do export with warning."""

    monkeypatch.chdir(tmp_path)

    with pytest.warns(UserWarning, match=pydantic_warning()):
        edata = ExportData(config={}, content="depth")

    meta = edata.generate_metadata(regsurf)
    assert "masterdata" not in meta

    # check that obj is created but no metadata is found
    out = edata.export(regsurf, name="mysurface")
    assert "mysurface" in out
    assert Path(out).exists()
    with pytest.raises(OSError, match="Cannot find requested metafile"):
        read_metadata(out)


def test_config_miss_required_fields(monkeypatch, tmp_path, globalconfig1, regsurf):
    """Global config exists but missing critical data; export file but skip metadata."""

    monkeypatch.chdir(tmp_path)

    cfg = globalconfig1.copy()

    del cfg["access"]
    del cfg["masterdata"]
    del cfg["model"]

    with pytest.warns(UserWarning, match=pydantic_warning()):
        edata = ExportData(config=cfg, content="depth")

    with pytest.warns(UserWarning):
        out = edata.export(regsurf, name="mysurface")

    assert "mysurface" in out

    with pytest.raises(OSError, match="Cannot find requested metafile"):
        read_metadata(out)


def test_config_stratigraphy_empty_entries_alias(globalconfig2, regsurf):
    """Test that empty entries in 'alias' is detected and warned and removed."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["alias"] += [None]

    exp = ExportData(config=cfg, content="depth", name="TopVolantis")
    metadata = exp.generate_metadata(regsurf)

    assert None not in metadata["data"]["alias"]


@pytest.mark.xfail(reason="stratigraphic_alias is not implemented")
def test_config_stratigraphy_empty_entries_stratigraphic_alias(globalconfig2, regsurf):
    """Test that empty entries in 'stratigraphic_alias' detected and warned."""

    # Note! stratigraphic_alias is not implemented, but we still check consistency

    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["stratigraphic_alias"] += [None]

    exp = ExportData(config=cfg, content="depth")
    metadata = exp.generate_metadata(regsurf)

    assert None not in metadata["data"]["stratigraphic_alias"]


def test_config_stratigraphy_empty_name(globalconfig2):
    """Test that empty 'name' is detected and warned."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["name"] = None

    with pytest.warns(UserWarning, match=pydantic_warning()):
        ExportData(config=cfg, content="depth")


def test_config_stratigraphy_stratigraphic_not_bool(globalconfig2):
    """Test that non-boolean 'stratigraphic' is detected and warned."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["stratigraphic"] = None

    with pytest.warns(UserWarning, match=pydantic_warning()):
        ExportData(config=cfg, content="depth")

    cfg["stratigraphy"]["TopVolantis"]["stratigraphic"] = "a string"

    with pytest.warns(UserWarning, match=pydantic_warning()):
        ExportData(config=cfg, content="depth")


def test_update_check_settings_shall_fail(globalconfig1):
    # pylint: disable=unexpected-keyword-arg
    with pytest.raises(TypeError):
        _ = ExportData(config=globalconfig1, stupid="str", content="depth")

    newsettings = {"invalidkey": "some"}
    some = ExportData(config=globalconfig1, content="depth")
    with pytest.raises(KeyError):
        some._update_check_settings(newsettings)


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

    # under primary initialisation
    kval = {key: value}
    with pytest.warns(UserWarning, match=expected_msg):
        ExportData(config=globalconfig1, content="depth", **kval)

    # under override
    with pytest.warns(UserWarning, match=expected_msg):
        edata = ExportData(config=globalconfig1, content="depth")
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
        )
        mymeta = exp.generate_metadata(regsurf)
        assert mymeta["access"]["classification"] == "restricted"
        assert mymeta["access"]["ssdl"]["rep_include"] is True

    # 'access_ssdl' is not allowed together with any combination of
    # 'classification' / 'rep_include' arguments
    with pytest.raises(ValueError, match="is not supported"):
        ExportData(
            access_ssdl={"access_level": "restricted"}, classification="internal"
        )
    with pytest.raises(ValueError, match="is not supported"):
        ExportData(access_ssdl={"rep_include": True}, rep_include=True)

    with pytest.raises(ValueError, match="is not supported"):
        ExportData(access_ssdl={"access_level": "restricted"}, rep_include=False)

    # using 'classification' / 'rep_include' as arguments is the preferred pattern
    exp = ExportData(
        config=globalconfig1, classification="restricted", rep_include=True
    )
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "restricted"
    assert mymeta["access"]["ssdl"]["rep_include"] is True


def test_classification(globalconfig1, regsurf):
    """Test that 'classification' is set correctly."""

    # test assumptions
    config = deepcopy(globalconfig1)
    assert config["access"]["classification"] == "internal"
    assert "access_level" not in config["access"]["ssdl"]

    # test that classification can be given directly and will override config
    exp = ExportData(config=config, classification="restricted")
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "restricted"

    # test that classification can be given through deprecated access_ssdl
    with pytest.warns(FutureWarning, match="'access_ssdl' argument is deprecated"):
        exp = ExportData(config=config, access_ssdl={"access_level": "restricted"})
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "restricted"

    # test that classification is taken from 'classification' in config if not provided
    exp = ExportData(config=config)
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "internal"

    # test that classification is taken from access.ssdl.access_level
    # in config if classification is not present
    del config["access"]["classification"]
    config["access"]["ssdl"]["access_level"] = "restricted"
    exp = ExportData(config=config)
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "restricted"

    # verify that classification is defaulted to internal
    exp = ExportData(config={})
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["classification"] == "internal"


def test_rep_include(globalconfig1, regsurf):
    """Test that 'classification' is set correctly."""

    # test assumptions
    assert globalconfig1["access"]["ssdl"]["rep_include"] is False

    # test that rep_include can be given directly and will override config
    exp = ExportData(config=globalconfig1, rep_include=True)
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["ssdl"]["rep_include"] is True

    # test that rep_include can be given through access_ssdl
    with pytest.warns(FutureWarning, match="'access_ssdl' argument is deprecated"):
        exp = ExportData(config=globalconfig1, access_ssdl={"rep_include": True})
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["ssdl"]["rep_include"] is True

    # test that rep_include is taken from config if not provided
    exp = ExportData(config=globalconfig1)
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["ssdl"]["rep_include"] is False

    # test that rep_include is defaulted False
    exp = ExportData(config={})
    mymeta = exp.generate_metadata(regsurf)
    assert mymeta["access"]["ssdl"]["rep_include"] is False


def test_unit_is_none(globalconfig1, regsurf):
    """Test that unit=None works and is translated into an enpty string"""
    eobj = ExportData(config=globalconfig1, unit=None)
    meta = eobj.generate_metadata(regsurf)
    assert meta["data"]["unit"] == ""


def test_content_not_given(globalconfig1, regsurf):
    """When content is not explicitly given, warning shall be issued."""
    eobj = ExportData(config=globalconfig1)
    with pytest.warns(UserWarning, match="The <content> is not provided"):
        mymeta = eobj.generate_metadata(regsurf)

    assert mymeta["data"]["content"] == "unset"


def test_content_given_init_or_later(globalconfig1, regsurf):
    """When content is not explicitly given, warning shall be issued."""
    eobj = ExportData(config=globalconfig1, content="time")
    mymeta = eobj.generate_metadata(regsurf)

    assert mymeta["data"]["content"] == "time"

    # override by adding content at generate_metadata
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
    with pytest.raises(ValueError, match="Found more than one content item"):
        eobj.generate_metadata(regsurf)


def test_content_valid_string(regsurf, globalconfig2):
    eobj = ExportData(config=globalconfig2, name="TopVolantis", content="depth")
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["content"] == "depth"
    assert "depth" not in mymeta["data"]


def test_seismic_content_require_seismic_data(globalconfig2, regsurf):
    eobj = ExportData(config=globalconfig2, content="seismic")
    with pytest.raises(pydantic.ValidationError, match="requires additional input"):
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
    with pytest.raises(ValueError, match="incorrectly formatted"):
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


def test_content_with_subfields(globalconfig2, polygons):
    """When subfield is given and allowed, it shall be produced to metadata."""
    eobj = ExportData(
        config=globalconfig2,
        name="Central Horst",
        content={"field_region": {"id": 1}},
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
    edata = ExportData(config=globalconfig1, workflow=workflow)
    meta = edata.generate_metadata(regsurf)
    assert meta["fmu"]["workflow"]["reference"] == workflow

    # doing actual export with a few ovverides
    edata = ExportData(config=globalconfig1)
    meta = edata.generate_metadata(regsurf, workflow="My test workflow")
    assert meta["fmu"]["workflow"]["reference"] == workflow


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

    # also test when setting directly in the method call
    mymeta = eobj.generate_metadata(regsurf, display_name="MyOtherDisplayName")

    assert mymeta["data"]["name"] == "MyName"
    assert mymeta["display"]["name"] == "MyOtherDisplayName"


def test_global_config_from_env(monkeypatch, global_config2_path, globalconfig1):
    """Testing getting global config from a file"""
    monkeypatch.setenv("FMU_GLOBAL_CONFIG", str(global_config2_path))

    edata = ExportData(content="depth")  # the env variable will override this
    assert "smda" in edata.config["masterdata"]
    assert edata.config["model"]["name"] == "ff"

    # do not use global config from environment when explicitly given
    edata = ExportData(config=globalconfig1, content="depth")
    assert edata.config["model"]["name"] == "Test"


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

    edata.export(regsurf)

    assert edata._metadata["fmu"]["realization"]["name"] == "realization-1"
    assert edata._metadata["fmu"]["realization"]["id"] == 1
    assert edata._metadata["fmu"]["iteration"]["name"] == "iter-0"
    assert edata._metadata["fmu"]["iteration"]["id"] == 0


def test_fmucontext_case_casepath(fmurun_prehook, rmsglobalconfig, regsurf):
    """
    Test fmu_context case when casepath is / is not explicitly given

    In the future we would like to not be able to update casepath outside
    of initialization, but it needs to be deprecated first.
    """
    assert FmuEnv.RUNPATH.value is None
    assert FmuEnv.EXPERIMENT_ID.value is not None

    # will give warning when casepath not provided
    with pytest.warns(UserWarning, match="Could not auto detect"):
        edata = ExportData(config=rmsglobalconfig, content="depth")

    # should still give warning when casepath not provided and create empty fmu metadata
    with pytest.warns(UserWarning, match="Could not auto detect"):
        meta = edata.generate_metadata(regsurf)
    assert "fmu" not in meta

    # no warning when casepath is provided and metadata is valid
    meta = edata.generate_metadata(regsurf, casepath=fmurun_prehook)
    assert "fmu" in meta
    assert meta["fmu"]["case"]["name"] == "somecasename"


def test_fmurun_attribute_inside_fmu(fmurun_w_casemetadata, rmsglobalconfig):
    """Test that _fmurun attribute is True when in fmu"""

    # check that ERT environment variable is not set
    assert FmuEnv.ENSEMBLE_ID.value is not None

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
    assert FmuEnv.EXPERIMENT_ID.value is not None

    edata = ExportData(config=rmsglobalconfig, content="depth")
    assert edata._fmurun is True
    assert edata.fmu_context == FmuContext.REALIZATION


def test_fmu_context_not_given_fetch_from_env_case(
    fmurun_prehook, rmsglobalconfig, regsurf
):
    """
    Test fmu_context not explicitly given, should be set to "case" when
    inside fmu and RUNPATH value not detected from the environment variables.
    """
    assert FmuEnv.RUNPATH.value is None
    assert FmuEnv.EXPERIMENT_ID.value is not None

    # will give warning when casepath not provided
    with pytest.warns(UserWarning, match="Could not auto detect"):
        edata = ExportData(config=rmsglobalconfig, content="depth")

    # test that it runs properly when casepath is provided
    edata = ExportData(config=rmsglobalconfig, content="depth", casepath=fmurun_prehook)
    assert edata._fmurun is True
    assert edata.fmu_context == FmuContext.CASE
    assert edata._rootpath == fmurun_prehook


def test_fmu_context_not_given_fetch_from_env_nonfmu(rmsglobalconfig):
    """
    Test fmu_context not explicitly given, should be set to "non-fmu" when
    outside fmu.
    """
    assert FmuEnv.RUNPATH.value is None
    assert FmuEnv.EXPERIMENT_ID.value is None

    edata = ExportData(config=rmsglobalconfig, content="depth")
    assert edata._fmurun is False
    assert edata.fmu_context == FmuContext.NON_FMU


def test_fmu_context_outside_fmu_input_overwrite(rmsglobalconfig):
    """
    For non-fmu run fmu_context should be overwritten when input
    is not "preprocessed"
    """
    edata = ExportData(
        config=rmsglobalconfig, content="depth", fmu_context="realization"
    )
    assert edata._fmurun is False
    assert edata.fmu_context == FmuContext.NON_FMU


def test_fmu_context_outside_fmu_no_input_overwrite(rmsglobalconfig):
    """
    For non-fmu run fmu_context should not be overwritten when input
    is "preprocessed"
    """
    edata = ExportData(
        config=rmsglobalconfig, content="depth", fmu_context="preprocessed"
    )
    assert edata._fmurun is False
    assert edata.fmu_context == FmuContext.PREPROCESSED


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
    edata2 = ExportData(content="depth")  # the env variable will override this
    meta2 = edata2.generate_metadata(regsurf, name="TopBlåbær")
    logger.debug("\n %s", prettyprint_dict(meta2))
    assert meta2["data"]["name"] == "TopBlåbær"
    assert meta2["masterdata"]["smda"]["field"][0]["identifier"] == "DRÅGØN"


def test_norwegian_letters_globalconfig_as_json(
    globalvars_norwegian_letters,
    regsurf,
):
    """Testing using norwegian letters in global config, with json output."""

    path, cfg, _ = globalvars_norwegian_letters
    os.chdir(path)

    ExportData.meta_format = "json"
    edata = ExportData(config=cfg, name="TopBlåbær", content="depth")

    result = pathlib.Path(edata.export(regsurf))
    metafile = result.parent / ("." + str(result.stem) + ".gri.json")
    with open(metafile, encoding="utf-8") as stream:
        assert "DRÅGØN" in stream.read()

    ExportData.meta_format = "yaml"  # reset


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
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
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

    edata = ExportData(config=globalconfig2, content="depth", forcefolder="/tmp/what")
    with pytest.raises(ValueError, match="Can't use absolute path as 'forcefolder'"):
        edata.generate_metadata(regsurf, name="x")

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
        content={"seismic": {"attribute": "attribute-value"}}, config=globalconfig2
    )
    meta = edata.generate_metadata(regsurf)
    assert meta["data"]["content"] == "seismic"
    assert meta["data"]["seismic"] == {"attribute": "attribute-value"}


def test_content_property_as_string_future_warning(globalconfig2, regsurf):
    edata = ExportData(content="property", config=globalconfig2)
    with pytest.warns(FutureWarning):
        edata.generate_metadata(regsurf)
