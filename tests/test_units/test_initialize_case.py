"""Test the dataio running from within RMS interactive as context.

In this case a user sits in RMS, which is in folder rms/model and runs
interactive. Hence the basepath will be ../../
"""

import logging
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from fmu.dataio import InitializeCase
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def test_initialize_case_barebone(globalconfig2):
    icase = InitializeCase(
        config=globalconfig2, rootfolder="", casename="", caseuser="MyUser"
    )
    assert icase.config == globalconfig2
    assert icase.rootfolder == ""
    assert icase.casename == ""
    assert icase.caseuser == "MyUser"
    assert not icase.description


def test_initialize_case_post_init(monkeypatch, fmurun, globalconfig2):
    monkeypatch.chdir(fmurun)
    caseroot = fmurun.parent.parent
    logger.info("Active folder is %s", fmurun)

    icase = InitializeCase(
        config=globalconfig2,
        rootfolder=caseroot,
        casename="mycase",
        caseuser="user",
        description="Some description",
    )
    logger.info("Casepath is %s", icase._casepath)

    assert icase._casepath == caseroot
    assert icase._pwd == fmurun
    assert icase._metafile == caseroot / "share/metadata/fmu_case.yml"


@pytest.mark.filterwarnings("ignore:The global configuration")
def test_initialize_case_post_init_bad_globalconfig(monkeypatch, fmurun, globalconfig2):
    monkeypatch.chdir(fmurun)
    logger.info("Active folder is %s", fmurun)
    caseroot = fmurun.parent.parent
    logger.info("Case folder is now %s", caseroot)

    config = deepcopy(globalconfig2)
    del config["masterdata"]

    with pytest.raises(ValidationError, match="masterdata"):
        InitializeCase(
            config=config,
            rootfolder=caseroot,
            casename="mycase",
            caseuser="user",
        )


def test_initialize_case_establish_metadata_files(monkeypatch, fmurun, globalconfig2):
    """Tests that the required directories are made when establishing the case"""
    monkeypatch.chdir(fmurun)
    logger.info("Active folder is %s", fmurun)
    caseroot = fmurun.parent.parent
    logger.info("Case folder is now %s", caseroot)

    icase = InitializeCase(
        config=globalconfig2, rootfolder=caseroot, casename="mycase", caseuser="user"
    )
    share_metadata = caseroot / "share/metadata"
    assert not share_metadata.exists()
    assert icase._establish_metadata_files()
    assert share_metadata.exists()
    assert not icase._metafile.exists()


def test_initialize_case_establish_metadata_files_exists(
    monkeypatch, fmurun, globalconfig2
):
    """Tests that _establish_metadata_files returns correctly if the share/metadata
    directory already exists."""
    monkeypatch.chdir(fmurun)
    logger.info("Active folder is %s", fmurun)
    caseroot = fmurun.parent.parent
    logger.info("Case folder is now %s", caseroot)

    icase = InitializeCase(
        config=globalconfig2, rootfolder=caseroot, casename="mycase", caseuser="user"
    )
    (caseroot / "share/metadata").mkdir(parents=True, exist_ok=True)
    assert icase._establish_metadata_files()
    assert not icase._metafile.exists()
    # Again but with fmu_case.yml created
    icase._metafile.touch()
    assert not icase._establish_metadata_files()
    assert icase._metafile.exists()


def test_initialize_case_generate_metadata(monkeypatch, fmurun, globalconfig2):
    monkeypatch.chdir(fmurun)
    logger.info("Active folder is %s", fmurun)
    myroot = fmurun.parent.parent.parent / "mycase"
    logger.info("Case folder is now %s", myroot)

    icase = InitializeCase(
        config=globalconfig2, rootfolder=myroot, casename="mycase", caseuser="user"
    )
    metadata = icase.generate_metadata()
    assert metadata
    assert metadata["fmu"]["case"]["name"] == "mycase"
    assert metadata["fmu"]["case"]["user"]["id"] == "user"


def test_initialize_case_generate_metadata_warn_if_exists(
    monkeypatch, fmurun_w_casemetadata, globalconfig2
):
    monkeypatch.chdir(fmurun_w_casemetadata)
    logger.info("Active folder is %s", fmurun_w_casemetadata)
    casemetafolder = fmurun_w_casemetadata.parent.parent

    icase = InitializeCase(
        config=globalconfig2,
        rootfolder=casemetafolder,
        casename="abc",
        caseuser="user",
    )
    with pytest.warns(UserWarning, match=r"The case metadata file already exists"):
        icase.generate_metadata()


def test_initialize_case_with_export(monkeypatch, globalconfig2, fmurun):
    monkeypatch.chdir(fmurun)
    caseroot = fmurun.parent.parent

    icase = InitializeCase(
        config=globalconfig2,
        rootfolder=caseroot,
        casename="MyCaseName",
        caseuser="MyUser",
        description="Some description",
    )
    fmu_case_yml = Path(icase.export())
    assert fmu_case_yml.exists()
    assert fmu_case_yml == caseroot / "share/metadata/fmu_case.yml"

    with open(fmu_case_yml) as stream:
        metadata = yaml.safe_load(stream)

    assert metadata["fmu"]["case"]["name"] == "MyCaseName"
    assert metadata["masterdata"]["smda"]["field"][0]["identifier"] == "DROGON"


def test_initialize_case_export_with_norsk_alphabet(monkeypatch, globalconfig2, fmurun):
    monkeypatch.chdir(fmurun)
    caseroot = fmurun.parent.parent

    icase = InitializeCase(
        config=globalconfig2,
        rootfolder=caseroot,
        casename="MyCaseName_with_Æ",
        caseuser="MyUser",
        description="Søme description",
    )
    globalconfig2["masterdata"]["smda"]["field"][0]["identifier"] = "æøå"

    fmu_case_yml = Path(icase.export())
    assert fmu_case_yml.exists()
    assert fmu_case_yml == caseroot / "share/metadata/fmu_case.yml"

    with open(fmu_case_yml) as stream:
        metadata = yaml.safe_load(stream)

    assert metadata["fmu"]["case"]["name"] == "MyCaseName_with_Æ"
    assert metadata["masterdata"]["smda"]["field"][0]["identifier"] == "æøå"

    # Check that special characters are encoded properly in stored metadatafile.
    # yaml.safe_load() seems to sort this out, but we want files on disk to be readable.
    # Therefore check by reading the raw file content.
    with open(fmu_case_yml) as stream:
        metadata_string = stream.read()

    assert "æøå" in metadata_string
