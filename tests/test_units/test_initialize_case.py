"""Test the dataio running from within RMS interactive as context.

In this case a user sits in RMS, which is in folder rms/model and runs
interactive. Hence the basepath will be ../../
"""
import logging
import os

import pytest

from fmu.dataio import InitializeCase
from fmu.dataio._utils import prettyprint_dict

logger = logging.getLogger(__name__)


def test_inicase_barebone(globalconfig2):

    icase = InitializeCase(globalconfig2)
    assert "Drogon" in str(icase.config)


def test_inicase_pwd_basepath(fmurun, globalconfig2):

    logger.info("Active folder is %s", fmurun)
    os.chdir(fmurun)

    icase = InitializeCase(globalconfig2)
    icase._establish_pwd_rootpath()

    logger.info("Rootpath is %s", icase._rootpath)

    assert icase._rootpath == fmurun.parent.parent
    assert icase._pwd == fmurun


def test_inicase_generate_case_metadata(fmurun, globalconfig2):

    logger.info("Active folder is %s", fmurun)
    os.chdir(fmurun)

    icase = InitializeCase(globalconfig2, verbosity="INFO")
    icase.generate_case_metadata()


def test_inicase_generate_case_metadata_exists_so_fails(
    fmurun_w_casemetadata, globalconfig2
):

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    icase = InitializeCase(globalconfig2, verbosity="INFO")
    with pytest.raises(ValueError):
        icase.generate_case_metadata()


def test_inicase_generate_case_metadata_exists_but_force(
    fmurun_w_casemetadata, globalconfig2
):

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)
    icase = InitializeCase(globalconfig2, verbosity="INFO")
    cur_case = icase._get_case_metadata()

    icase.generate_case_metadata(force=True)
    icase.export(force=True)
    new_case = icase._get_case_metadata()
    logger.debug("Current case metadata\n%s", prettyprint_dict(cur_case["masterdata"]))
    logger.debug("New case metadata\n%s", prettyprint_dict(new_case["masterdata"]))

    smda_old = cur_case["masterdata"]["smda"]
    smda_new = new_case["masterdata"]["smda"]
    for key in smda_old.keys():
        assert smda_new[key] == smda_old[key]

    assert cur_case["class"] == new_case["class"]

    assert cur_case["fmu"]["case"]["user"]["id"] == "peesv"
