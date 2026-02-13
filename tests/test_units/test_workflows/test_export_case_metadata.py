"""Test the dataio running from within RMS interactive as context.

In this case a user sits in RMS, which is in folder rms/model and runs
interactive. Hence the basepath will be ../../
"""

import getpass
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from pydantic import ValidationError
from pytest import MonkeyPatch

from fmu.dataio._workflows.case.export_case_metadata import ExportCaseMetadata

logger = logging.getLogger(__name__)


def test_crease_case_metadata_barebone(drogon_global_config: dict[str, Any]) -> None:
    case = ExportCaseMetadata(config=drogon_global_config, rootfolder="", casename="")
    assert isinstance(case.config, GlobalConfiguration)
    assert case.config == GlobalConfiguration.model_validate(drogon_global_config)
    assert case.rootfolder == ""
    assert case.casename == ""


def test_export_case_metadata_post_init(
    monkeypatch: MonkeyPatch, fmurun: Path, drogon_global_config: dict[str, Any]
) -> None:
    monkeypatch.chdir(fmurun)
    caseroot = fmurun.parent.parent
    logger.info("Active folder is %s", fmurun)

    icase = ExportCaseMetadata(
        config=drogon_global_config,
        rootfolder=caseroot,
        casename="mycase",
    )
    logger.info("Casepath is %s", icase._casepath)

    assert icase._casepath == caseroot
    assert icase._metafile == caseroot / "share/metadata/fmu_case.yml"


@pytest.mark.filterwarnings("ignore:The global configuration")
def test_export_case_metadata_post_init_bad_globalconfig(
    monkeypatch: MonkeyPatch, fmurun: Path, drogon_global_config: dict[str, Any]
) -> None:
    monkeypatch.chdir(fmurun)
    logger.info("Active folder is %s", fmurun)
    caseroot = fmurun.parent.parent
    logger.info("Case folder is now %s", caseroot)

    config = deepcopy(drogon_global_config)
    del config["masterdata"]

    with pytest.raises(ValidationError, match="masterdata"):
        ExportCaseMetadata(
            config=config,
            rootfolder=caseroot,
            casename="mycase",
        )


def test_export_case_metadata_establish_metadata_files(
    monkeypatch: MonkeyPatch, fmurun: Path, drogon_global_config: dict[str, Any]
) -> None:
    """Tests that the required directories are made when establishing the case"""
    monkeypatch.chdir(fmurun)
    logger.info("Active folder is %s", fmurun)
    caseroot = fmurun.parent.parent
    logger.info("Case folder is now %s", caseroot)

    icase = ExportCaseMetadata(
        config=drogon_global_config, rootfolder=caseroot, casename="mycase"
    )
    share_metadata = caseroot / "share/metadata"
    assert not share_metadata.exists()
    assert icase._establish_metadata_files()
    assert share_metadata.exists()
    assert not icase._metafile.exists()


def test_export_case_metadata_establish_metadata_files_exists(
    monkeypatch: MonkeyPatch, fmurun: Path, drogon_global_config: dict[str, Any]
) -> None:
    """Tests that _establish_metadata_files returns correctly if the share/metadata
    directory already exists."""
    monkeypatch.chdir(fmurun)
    logger.info("Active folder is %s", fmurun)
    caseroot = fmurun.parent.parent
    logger.info("Case folder is now %s", caseroot)

    icase = ExportCaseMetadata(
        config=drogon_global_config, rootfolder=caseroot, casename="mycase"
    )
    (caseroot / "share/metadata").mkdir(parents=True, exist_ok=True)
    assert icase._establish_metadata_files()
    assert not icase._metafile.exists()
    # Again but with fmu_case.yml created
    icase._metafile.touch()
    assert not icase._establish_metadata_files()
    assert icase._metafile.exists()


def test_export_case_metadata_generate_metadata(
    monkeypatch: MonkeyPatch, fmurun: Path, drogon_global_config: dict[str, Any]
) -> None:
    monkeypatch.chdir(fmurun)
    logger.info("Active folder is %s", fmurun)
    myroot = fmurun.parent.parent.parent / "mycase"
    logger.info("Case folder is now %s", myroot)

    icase = ExportCaseMetadata(
        config=drogon_global_config, rootfolder=myroot, casename="mycase"
    )
    metadata = icase.generate_metadata()
    assert metadata
    assert metadata["fmu"]["case"]["name"] == "mycase"
    assert metadata["fmu"]["case"]["user"]["id"] == getpass.getuser()


def test_export_case_metadata_generate_metadata_warn_if_exists(
    monkeypatch: MonkeyPatch,
    fmurun_w_casemetadata: Path,
    drogon_global_config: dict[str, Any],
) -> None:
    logger.info("Active folder is %s", fmurun_w_casemetadata)
    casemetafolder = fmurun_w_casemetadata.parent.parent

    icase = ExportCaseMetadata(
        config=drogon_global_config,
        rootfolder=casemetafolder,
        casename="abc",
    )
    with pytest.warns(UserWarning, match="Using existing case metadata from casepath:"):
        icase.generate_metadata()


def test_export_case_metadata_with_export(
    monkeypatch: MonkeyPatch, drogon_global_config: dict[str, Any], fmurun: Path
) -> None:
    monkeypatch.chdir(fmurun)
    caseroot = fmurun.parent.parent

    icase = ExportCaseMetadata(
        config=drogon_global_config,
        rootfolder=caseroot,
        casename="MyCaseName",
    )
    fmu_case_yml = Path(icase.export())
    assert fmu_case_yml.exists()
    assert fmu_case_yml == caseroot / "share/metadata/fmu_case.yml"

    with open(fmu_case_yml) as stream:
        metadata = yaml.safe_load(stream)

    assert metadata["fmu"]["case"]["name"] == "MyCaseName"
    assert metadata["masterdata"]["smda"]["field"][0]["identifier"] == "DROGON"


def test_export_case_metadata_export_with_norsk_alphabet(
    monkeypatch: MonkeyPatch, drogon_global_config: dict[str, Any], fmurun: Path
) -> None:
    monkeypatch.chdir(fmurun)
    caseroot = fmurun.parent.parent

    drogon_global_config["masterdata"]["smda"]["field"][0]["identifier"] = "æøå"
    case = ExportCaseMetadata(
        config=drogon_global_config,
        rootfolder=caseroot,
        casename="MyCaseName_with_Æ",
    )

    fmu_case_yml = Path(case.export())
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
