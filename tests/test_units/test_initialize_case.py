"""Test the dataio running from within RMS interactive as context.

In this case a user sits in RMS, which is in folder rms/model and runs
interactive. Hence the basepath will be ../../
"""
import logging
import os

import pytest
import yaml

from fmu.dataio import InitializeCase
from fmu.dataio._utils import prettyprint_dict

logger = logging.getLogger(__name__)


def test_inicase_barebone(globalconfig2):

    icase = InitializeCase(config=globalconfig2, verbosity="INFO")
    assert "Drogon" in str(icase.config)


def test_inicase_pwd_basepath(fmurun, globalconfig2):

    logger.info("Active folder is %s", fmurun)
    os.chdir(fmurun)

    icase = InitializeCase(config=globalconfig2, verbosity="INFO")
    with pytest.warns(UserWarning):
        icase._establish_pwd_casepath()

    logger.info("Casepath is %s", icase._casepath)

    assert icase._casepath == fmurun.parent.parent
    assert icase._pwd == fmurun


def test_inicase_pwd_basepath_explicit(fmurun, globalconfig2):
    """The casepath should in general be explicit."""
    logger.info("Active folder is %s", fmurun)
    os.chdir(fmurun)

    myroot = fmurun

    icase = InitializeCase(
        config=globalconfig2, verbosity="INFO", rootfolder=myroot, casename="mycase"
    )
    icase._establish_pwd_casepath()

    logger.info("Casepath is %s", icase._casepath)

    assert icase._casepath == myroot
    assert icase._pwd == fmurun


def test_inicase_update_settings(fmurun, globalconfig2):
    """Update self attributes after init."""
    logger.info("Active folder is %s", fmurun)
    os.chdir(fmurun)
    myroot = fmurun / "mycase"

    icase = InitializeCase(config=globalconfig2, verbosity="INFO", rootfolder=myroot)
    kwargs = {"rootfolder": "/tmp"}
    icase._update_settings(newsettings=kwargs)

    assert icase.rootfolder == "/tmp"

    kwargs = {"casename": "Here we go"}
    icase._update_settings(newsettings=kwargs)

    assert icase.casename == "Here we go"


def test_inicase_update_settings_correct_key_wrong_type(fmurun, globalconfig2):
    """Update self attributes after init, but with wrong type."""
    logger.info("Active folder is %s", fmurun)
    os.chdir(fmurun)
    myroot = fmurun / "mycase"

    icase = InitializeCase(config=globalconfig2, verbosity="INFO", rootfolder=myroot)
    kwargs = {"rootfolder": 1234567}
    with pytest.raises(ValueError, match=r"The value of '"):
        icase._update_settings(newsettings=kwargs)


def test_inicase_update_settings_shall_fail(fmurun, globalconfig2):
    """Update self attributes after init, but using an invalid key."""
    logger.info("Active folder is %s", fmurun)
    os.chdir(fmurun)
    myroot = fmurun / "mycase"

    icase = InitializeCase(config=globalconfig2, verbosity="INFO", rootfolder=myroot)
    kwargs = {"invalidfolder": "/tmp"}
    with pytest.raises(KeyError):
        icase._update_settings(newsettings=kwargs)


def test_inicase_generate_case_metadata(fmurun, globalconfig2):

    logger.info("Active folder is %s", fmurun)
    os.chdir(fmurun)
    myroot = fmurun.parent.parent.parent / "mycase"
    logger.info("Case folder is now %s", myroot)

    icase = InitializeCase(globalconfig2, verbosity="INFO")
    icase.generate_case_metadata()


def test_inicase_generate_case_metadata_exists_so_fails(
    fmurun_w_casemetadata, globalconfig2
):

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)
    logger.info("Folder is %s", fmurun_w_casemetadata)
    casemetafolder = fmurun_w_casemetadata.parent.parent

    icase = InitializeCase(globalconfig2, verbosity="INFO")
    with pytest.warns(UserWarning, match=r"The metadata file already exist!"):
        icase.generate_case_metadata(rootfolder=casemetafolder)


def test_inicase_generate_case_metadata_exists_but_force(
    fmurun_w_casemetadata, globalconfig2
):

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)
    logger.info("Folder is %s", fmurun_w_casemetadata)
    casemetafolder = fmurun_w_casemetadata.parent.parent
    old_metafile = casemetafolder / "share/metadata/fmu_case.yml"

    with open(old_metafile, "r", encoding="utf-8") as stream:
        old_content = yaml.safe_load(stream)

    icase = InitializeCase(globalconfig2, verbosity="INFO")
    icase.export(
        rootfolder=casemetafolder,
        force=True,
        casename="ertrun1",
        caseuser="guffen",
        description="My curious case",
        restart_from="Jurassic era",
    )

    new_metafile = casemetafolder / "share/metadata/fmu_case.yml"
    with open(new_metafile, "r", encoding="utf-8") as stream:
        new_content = yaml.safe_load(stream)

    logger.debug("\n%s\n", prettyprint_dict(old_content))
    logger.debug("\n%s\n", prettyprint_dict(new_content))

    assert old_content["class"] == new_content["class"]
    assert old_content["fmu"]["case"]["uuid"] != new_content["fmu"]["case"]["uuid"]
