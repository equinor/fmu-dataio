"""Test the dataio ExportData etc from the dataio.py module"""
import logging
import os

import pytest
import yaml

from fmu.dataio.dataio import ExportData, ValidationError

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


def test_content_is_invalid(globalconfig1):

    kval = {"content": "not_legal"}
    with pytest.raises(ValidationError, match=r"Invalid content"):
        ExportData(config=globalconfig1, **kval)


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
