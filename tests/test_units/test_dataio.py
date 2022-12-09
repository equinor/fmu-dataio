"""Test the dataio ExportData etc from the dataio.py module."""
import logging
import os
import pathlib
import sys

import pytest
import yaml

from fmu.dataio._utils import prettyprint_dict
from fmu.dataio.dataio import ExportData, ValidationError, read_metadata

# pylint: disable=no-member

logger = logging.getLogger(__name__)


def test_generate_metadata_simple(globalconfig1):
    """Test generating metadata"""

    default_fformat = ExportData.grid_fformat
    ExportData.grid_fformat = "grdecl"

    logger.info("Config in: \n%s", globalconfig1)

    edata = ExportData(config=globalconfig1)

    assert edata.config["model"]["name"] == "Test"

    assert edata.meta_format == "yaml"
    assert edata.grid_fformat == "grdecl"
    assert edata.name == ""

    ExportData.grid_fformat = default_fformat  # reset


def test_missing_or_wrong_config_exports_with_warning(regsurf):
    """In case a config is missing, or is invalid, do export with warning."""

    with pytest.warns(
        PendingDeprecationWarning, match="One or more keys required for valid metadata"
    ):
        edata = ExportData(config={})

    with pytest.warns(PendingDeprecationWarning, match="One or more"):
        meta = edata.generate_metadata(regsurf)

    assert "masterdata" not in meta

    with pytest.warns(PendingDeprecationWarning, match="One or more"):
        out = edata.export(regsurf, name="mysurface")

    assert "mysurface" in out

    with pytest.raises(OSError, match="Cannot find requested metafile"):
        read_metadata(out)


def test_update_check_settings_shall_fail(globalconfig1):

    # pylint: disable=unexpected-keyword-arg
    with pytest.raises(TypeError):
        _ = ExportData(config=globalconfig1, stupid="str")

    newsettings = {"invalidkey": "some"}
    some = ExportData(config=globalconfig1)
    with pytest.raises(KeyError):
        some._update_check_settings(newsettings)


@pytest.mark.parametrize(
    "key, value, wtype, expected_msg",
    [
        (
            "runpath",
            "some",
            PendingDeprecationWarning,
            r"The 'runpath' key has currently no function",
        ),
        (
            "grid_model",
            "some",
            PendingDeprecationWarning,
            r"The 'grid_model' key has currently no function",
        ),
    ],
)
def test_deprecated_keys(globalconfig1, regsurf, key, value, wtype, expected_msg):
    """Some keys shall raise a DeprecationWarning or similar."""

    # under primary initialisation
    kval = {key: value}
    with pytest.warns(wtype, match=expected_msg):
        _ = ExportData(config=globalconfig1, **kval)

    # under override
    with pytest.warns(wtype, match=expected_msg):
        edata = ExportData(config=globalconfig1)
        edata.generate_metadata(regsurf, **kval)


def test_content_invalid_string(globalconfig1):
    with pytest.raises(ValidationError, match=r"Invalid content"):
        ExportData(config=globalconfig1, content="not_valid")


def test_content_invalid_dict(globalconfig1):
    with pytest.raises(ValidationError, match=r"Invalid content"):
        ExportData(
            config=globalconfig1, content={"not_valid": {"some_key": "some_value"}}
        )


def test_content_valid_string(regsurf, globalconfig2):
    eobj = ExportData(config=globalconfig2, name="TopVolantis", content="seismic")
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["content"] == "seismic"
    assert "seismic" not in mymeta["data"]


def test_content_valid_dict(regsurf, globalconfig2):
    """Test for incorrectly formatted dict.

    When a dict is given, there shall be one key which is the content, and there shall
    be one value, which shall be a dictionary containing content-specific attributes."""

    eobj = ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content={
            "seismic": {
                "attribute": "myattribute",
                "zrange": 12.0,
                "stacking_offset": "0-15",
            }
        },
    )
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["content"] == "seismic"
    assert mymeta["data"]["seismic"] == {
        "attribute": "myattribute",
        "zrange": 12.0,
        "stacking_offset": "0-15",
    }


def test_content_is_a_wrongly_formatted_dict(globalconfig2):
    """When content is a dict, it shall have one key with one dict as value."""
    with pytest.raises(ValueError, match="incorrectly formatted"):
        ExportData(
            config=globalconfig2,
            name="TopVolantis",
            content={"seismic": "myvalue"},
        )


def test_content_is_dict_with_wrong_types(globalconfig2):
    """When content is a dict, it shall have right types for known keys."""
    with pytest.raises(ValidationError):
        ExportData(
            config=globalconfig2,
            name="TopVolantis",
            content={
                "seismic": {
                    "stacking_offset": 123.4,  # not a string
                }
            },
        )


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
            verbosity="DEBUG",
        )
        mymeta = eobj.generate_metadata(regsurf)

    # deprecated 'offset' replaced with 'stacking_offset'
    assert "offset" not in mymeta["data"]["seismic"]
    assert mymeta["data"]["seismic"] == {
        "stacking_offset": "0-15",
    }


def test_global_config_from_env(globalconfig_asfile):
    """Testing getting global config from a file"""
    os.environ["FMU_GLOBAL_CONFIG"] = globalconfig_asfile
    edata = ExportData()  # the env variable will override this
    assert "smda" in edata.config["masterdata"]

    del os.environ["FMU_GLOBAL_CONFIG"]


def test_settings_config_from_env(tmp_path, rmsglobalconfig, regsurf):
    """Testing getting user settings config from a file via env variable."""

    settings = dict()
    settings["name"] = "MyFancyName"
    settings["tagname"] = "MyFancyTag"
    settings["workflow"] = "Some work flow"
    settings["config"] = rmsglobalconfig

    with open(tmp_path / "mysettings.yml", "w") as stream:
        yaml.dump(settings, stream)

    os.environ["FMU_DATAIO_CONFIG"] = str(tmp_path / "mysettings.yml")
    edata = ExportData(verbosity="INFO")  # the env variable will override this
    assert edata.name == "MyFancyName"

    meta = edata.generate_metadata(regsurf)
    assert "myfancyname--myfancytag" in meta["file"]["relative_path"]

    del os.environ["FMU_DATAIO_CONFIG"]


def test_settings_and_global_config_from_env(tmp_path, rmsglobalconfig, regsurf):
    """Testing getting user settings config ands global from a env -> file."""

    settings = dict()
    settings["name"] = "MyFancyName"
    settings["tagname"] = "MyFancyTag"
    settings["workflow"] = "Some work flow"
    settings["config"] = rmsglobalconfig

    with open(tmp_path / "mysettings.yml", "w") as stream:
        yaml.dump(settings, stream)

    with open(tmp_path / "global_variables.yml", "w") as stream:
        yaml.dump(rmsglobalconfig, stream)

    os.environ["FMU_GLOBAL_CONFIG"] = str(tmp_path / "global_variables.yml")
    os.environ["FMU_DATAIO_CONFIG"] = str(tmp_path / "mysettings.yml")

    edata = ExportData(verbosity="INFO")  # the env variable will override this
    assert edata.name == "MyFancyName"

    meta = edata.generate_metadata(regsurf)
    assert "myfancyname--myfancytag" in meta["file"]["relative_path"]

    del os.environ["FMU_DATAIO_CONFIG"]
    del os.environ["FMU_GLOBAL_CONFIG"]


def test_settings_config_from_env_invalid(tmp_path, rmsglobalconfig):
    """Testing getting user settings config from a file but some invalid stuff."""

    settings = dict()
    settings["invalid"] = "MyFancyName"
    settings["workflow"] = "Some work flow"
    settings["config"] = rmsglobalconfig

    with open(tmp_path / "mysettings.yml", "w") as stream:
        yaml.dump(settings, stream)

    os.environ["FMU_DATAIO_CONFIG"] = str(tmp_path / "mysettings.yml")
    with pytest.raises(ValidationError):
        _ = ExportData(verbosity="INFO")

    del os.environ["FMU_DATAIO_CONFIG"]


def test_norwegian_letters_globalconfig(globalvars_norw_letters, regsurf):
    """Testing using norwegian letters in global config.

    Note that fmu.config utilities yaml_load() is applied to read cfg (cf conftest.py)
    """

    path, cfg, cfg_asfile = globalvars_norw_letters
    os.chdir(path)

    edata = ExportData(config=cfg, name="TopBlåbær")
    meta = edata.generate_metadata(regsurf)
    logger.debug("\n %s", prettyprint_dict(meta))
    assert meta["data"]["name"] == "TopBlåbær"
    assert meta["masterdata"]["smda"]["field"][0]["identifier"] == "DRÅGØN"

    # export to file and reread as raw
    result = pathlib.Path(edata.export(regsurf))
    metafile = result.parent / ("." + str(result.stem) + ".gri.yml")
    with open(metafile, "r", encoding="utf-8") as stream:
        stuff = stream.read()
    assert "DRÅGØN" in stuff

    # read file as global config

    os.environ["FMU_GLOBAL_CONFIG"] = cfg_asfile
    edata2 = ExportData()  # the env variable will override this
    meta2 = edata2.generate_metadata(regsurf, name="TopBlåbær")
    logger.debug("\n %s", prettyprint_dict(meta2))
    assert meta2["data"]["name"] == "TopBlåbær"
    assert meta2["masterdata"]["smda"]["field"][0]["identifier"] == "DRÅGØN"

    del os.environ["FMU_GLOBAL_CONFIG"]


def test_norwegian_letters_globalconfig_as_json(globalvars_norw_letters, regsurf):
    """Testing using norwegian letters in global config, with json output."""

    path, cfg, _ = globalvars_norw_letters
    os.chdir(path)

    ExportData.meta_format = "json"
    edata = ExportData(config=cfg, name="TopBlåbær")

    result = pathlib.Path(edata.export(regsurf))
    metafile = result.parent / ("." + str(result.stem) + ".gri.json")
    with open(metafile, "r", encoding="utf-8") as stream:
        stuff = stream.read()
    assert "DRÅGØN" in stuff

    ExportData.meta_format = "yaml"  # reset


def test_establish_pwd_runpath(tmp_path, globalconfig2):
    """Testing pwd and rootpath from RMS"""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    edata = ExportData(config=globalconfig2)
    edata._establish_pwd_rootpath()

    assert edata._rootpath == rmspath.parent.parent

    ExportData._inside_rms = False  # reset


@pytest.mark.skipif("win" in sys.platform, reason="Windows tests have no /tmp")
def test_forcefolder(tmp_path, globalconfig2, regsurf):
    """Testing the forcefolder mechanism."""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    edata = ExportData(config=globalconfig2, forcefolder="whatever")
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
    edata = ExportData(config=globalconfig2, forcefolder="/tmp/what")
    with pytest.raises(ValueError):
        meta = edata.generate_metadata(regsurf, name="x")

    ExportData.allow_forcefolder_absolute = True
    edata = ExportData(config=globalconfig2, forcefolder="/tmp/what")
    with pytest.warns(UserWarning, match="absolute paths in forcefolder is not rec"):
        meta = edata.generate_metadata(regsurf, name="y")

    assert (
        meta["file"]["relative_path"]
        == meta["file"]["absolute_path"]
        == "/tmp/what/y.gri"
    )
    ExportData.allow_forcefolder_absolute = False  # reset
    ExportData._inside_rms = False
