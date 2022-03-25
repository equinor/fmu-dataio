"""Test the dataio ExportData etc from the dataio.py module"""
import logging
import os

import pytest

from fmu.dataionew._utils import C, G, S
from fmu.dataionew.dataionew import ExportData, ValidationError

# pylint: disable=no-member

logger = logging.getLogger(__name__)


def test_generate_metadata_simple(globalconfig1):
    """Test generating metadata"""

    ExportData.grid_fformat = "grdecl"

    logger.info("Config in: \n%s", globalconfig1)

    edata = ExportData(config=globalconfig1)

    assert edata.cfg[G]["model"]["name"] == "Test"

    assert edata.cfg[C]["meta_format"] == "yaml"
    assert edata.cfg[C]["grid_fformat"] == "grdecl"
    assert edata.cfg[S]["name"] == ""


def test_update_check_settings_shall_fail(internalcfg2):

    # pylint: disable=unexpected-keyword-arg
    with pytest.raises(TypeError):
        _ = ExportData(config=internalcfg2[G], stupid="str")

    newsettings = {"invalidkey": "some"}
    with pytest.raises(ValueError):
        ExportData._update_check_settings("dummy", newsettings)


@pytest.mark.parametrize(
    "key, value, wtype, expected_msg",
    [
        (
            "casepath",
            "some",
            DeprecationWarning,
            r"The 'casepath' key is deprecated",
        ),
        (
            "context",
            "some",
            PendingDeprecationWarning,
            r"The 'context' key has currently no function",
        ),
    ],
)
def test_deprecated_keys(internalcfg2, regsurf, key, value, wtype, expected_msg):
    """Some keys shall raise a DeprecationWarning or similar."""

    # under primary initialisation
    kval = {key: value}
    with pytest.warns(wtype, match=expected_msg):
        _ = ExportData(config=internalcfg2[G], **kval)

    # under override
    with pytest.warns(wtype, match=expected_msg):
        edata = ExportData(config=internalcfg2[G])
        edata.generate_metadata(regsurf, **kval)


def test_content_is_invalid(internalcfg2):

    kval = {"content": "not_legal"}
    with pytest.raises(ValidationError, match=r"seems like 'content' value is illegal"):
        ExportData(config=internalcfg2[G], **kval)


def test_global_config_from_env(globalconfig_asfile):
    """Testing getting global config from a file"""
    os.environ["FMU_GLOBAL_CONFIG"] = globalconfig_asfile
    edata = ExportData()  # the env variable will override this
    assert "smda" in edata.cfg["GLOBVAR"]["masterdata"]


def test_establish_pwd_runpath(tmp_path, globalconfig2):
    """Testing pwd and basepath from RMS"""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    edata = ExportData(config=globalconfig2)
    # edata._establish_pwd_basepath()

    print("\nXXXXX\n", edata.basepath.absolute())
    ExportData._inside_rms = False  # reset
