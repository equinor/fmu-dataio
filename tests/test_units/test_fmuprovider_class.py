"""Test the FmuProvider class applied the _metadata.py module"""

import logging
import os
from pathlib import Path

import fmu.dataio as dataio
import pytest

# from conftest import pretend_ert_env_run1
from fmu.dataio._definitions import FmuContext
from fmu.dataio._fmu_provider import RESTART_PATH_ENVNAME, FmuEnv, FmuProvider

logger = logging.getLogger(__name__)

FOLDERTREE = "/scratch/myfield/case/realization-13/iter-2/"


def test_get_folderlist_from_path():
    """Test static method on getting folders from a path"""
    ftree = Path(FOLDERTREE)
    mylist = FmuProvider._get_folderlist_from_path(ftree)
    assert mylist[-1] == "iter-2"
    assert mylist[-3] == "case"
    assert mylist[0] == "scratch"


def test_get_folderlist_from_ert_runpath(monkeypatch):
    """Test static method on getting folders from a _ERT_RUNPATH env variable"""
    logger.debug("Set ENV for RUNPATH as %s", FmuEnv.RUNPATH.keyname)
    monkeypatch.setenv(FmuEnv.RUNPATH.keyname, FOLDERTREE)
    mylist = FmuProvider._get_folderlist_from_runpath_env()
    assert mylist[-1] == "iter-2"
    assert mylist[-3] == "case"


def test_fmuprovider_no_provider():
    """Testing the FmuProvider where no ERT context is found from env variables."""

    myfmu = FmuProvider(
        model="Model2",
        fmu_context=FmuContext.REALIZATION,
        casepath_proposed="",
        include_ertjobs=False,
        forced_realization=None,
        workflow="some work flow",
    )
    assert myfmu.get_provider() is None


def test_fmuprovider_ert_provider_guess_casemeta_path(fmurun):
    """The casepath input is empty, but try guess from ERT RUNPATH without success.

    Since there are mot metadata here, this will issue a warning
    """
    os.chdir(fmurun)
    with pytest.warns(UserWarning, match="Case metadata does not exist"):
        myfmu = FmuProvider(
            model="Model2",
            fmu_context=FmuContext.REALIZATION,
            casepath_proposed="",  # if casepath is undef, try deduce from, _ERT_RUNPATH
            include_ertjobs=False,
            forced_realization=None,
            workflow="some work flow",
        )

    assert myfmu.get_provider() == "ERT"
    assert myfmu._stage == "realization"  # i.e. being a so-called forward model
    assert not myfmu.get_metadata()
    assert myfmu.get_casepath() == ""


def test_fmuprovider_ert_provider_missing_parameter_txt(
    fmurun_w_casemetadata, globalconfig1
):
    """Test for an ERT case, when missing file parameter.txt (e.g. pred. run)"""

    os.chdir(fmurun_w_casemetadata)

    # delete the file for this test
    (fmurun_w_casemetadata / "parameters.txt").unlink()

    with pytest.warns(UserWarning, match="parameters.txt file was not found"):
        myfmu = FmuProvider(
            model="Model2",
            fmu_context=FmuContext.REALIZATION,
            include_ertjobs=True,
            workflow="some work flow",
        )
    assert myfmu._case_name == "ertrun1"
    assert myfmu._real_name == "realization-0"
    assert myfmu._real_id == 0


def test_fmuprovider_arbitrary_iter_name(fmurun_w_casemetadata_pred):
    """Test iteration block is correctly set, also with arbitrary iteration names."""

    os.chdir(fmurun_w_casemetadata_pred)
    myfmu = FmuProvider(
        model="Model2",
        fmu_context=FmuContext.REALIZATION,
        include_ertjobs=True,
        workflow="some work flow",
    )
    assert myfmu._case_name == "ertrun1"
    assert myfmu._real_name == "realization-0"
    assert myfmu._real_id == 0
    assert myfmu._iter_name == "pred"
    assert not myfmu._iter_id
    assert (
        myfmu._case_metadata["fmu"]["case"]["uuid"]
        == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"
    )


def test_fmuprovider_prehook_case(tmp_path, globalconfig2, fmurun_prehook):
    """The fmu run case metadata is initialized with Initialize case; then get provider.

    A typical prehook section in a ERT run is to establish case metadata, and then
    subsequent hook workflows should still recognize this as an ERT run, altough
    no iter and realization folders exists. This requires fmu_contact=case* and that
    key casepath_proposed is given explicitly!.

    I *may* be that this behaviour can be removed in near future, since the ERT env
    variables now will tell us that this is an active ERT run.
    """
    caseroot = tmp_path / "prehook"
    caseroot.mkdir(parents=True)
    os.chdir(caseroot)

    icase = dataio.InitializeCase(
        config=globalconfig2,
        rootfolder=caseroot,
        casename="MyCaseName",
        caseuser="MyUser",
        description="Some description",
    )
    exp = icase.export()

    casemetafile = caseroot / "share/metadata/fmu_case.yml"

    assert casemetafile.is_file()
    assert exp == str(casemetafile.resolve())

    os.chdir(fmurun_prehook)
    logger.debug("Case root proposed is: %s", caseroot)
    myfmu = FmuProvider(
        model="Model567",
        fmu_context=FmuContext.CASE,
        include_ertjobs=False,
        workflow="some work flow",
        casepath_proposed=caseroot,
    )

    assert myfmu._case_name == "prehook"
    assert myfmu._real_name == ""


def test_fmuprovider_detect_no_case_metadata(fmurun):
    """Testing the case metadata file which is not found here.

    That will still provide a file path but the metadata will be {} i.e. empty
    """
    os.chdir(fmurun)

    with pytest.warns(UserWarning):
        myfmu = FmuProvider(
            model="Model567",
            fmu_context=FmuContext.REALIZATION,
        )
    assert myfmu._case_name == "ertrun1"
    assert myfmu._real_name == "realization-0"
    assert myfmu._real_id == 0
    assert not myfmu._case_metadata


def test_fmuprovider_valid_restart_env(monkeypatch, fmurun_w_casemetadata, fmurun_pred):
    """Testing the scenario given a valid RESTART_FROM_PATH environment variable

    This shall give the correct restart_from uuid
    """
    os.chdir(fmurun_w_casemetadata)
    fmu_restart_from = FmuProvider(
        model="Model with restart", fmu_context=FmuContext.REALIZATION
    )

    monkeypatch.setenv(RESTART_PATH_ENVNAME, str(fmurun_w_casemetadata))

    os.chdir(fmurun_pred)
    fmu_restart = FmuProvider(model="Modelrun", fmu_context=FmuContext.REALIZATION)

    assert (
        fmu_restart._metadata["iteration"]["restart_from"]
        == fmu_restart_from._metadata["iteration"]["uuid"]
    )


def test_fmuprovider_invalid_restart_env(
    monkeypatch, fmurun_w_casemetadata, fmurun_pred
):
    """Testing the scenario given invalid RESTART_FROM_PATH environment variable

    The iteration metadata will not contain restart_from key
    """
    os.chdir(fmurun_w_casemetadata)

    _ = FmuProvider(model="Model with restart", fmu_context=FmuContext.REALIZATION)

    monkeypatch.setenv(RESTART_PATH_ENVNAME, "/path/to/somewhere/invalid")

    os.chdir(fmurun_pred)
    fmu_restart = FmuProvider(model="Modelrun", fmu_context=FmuContext.REALIZATION)
    assert "restart_from" not in fmu_restart._metadata["iteration"]


def test_fmuprovider_no_restart_env(monkeypatch, fmurun_w_casemetadata, fmurun_pred):
    """Testing the scenario without RESTART_FROM_PATH environment variable

    The iteration metadata will not contain restart_from key
    """
    os.chdir(fmurun_w_casemetadata)

    _ = FmuProvider(model="Model with restart", fmu_context=FmuContext.REALIZATION)

    monkeypatch.setenv(RESTART_PATH_ENVNAME, "/path/to/somewhere/invalid")
    monkeypatch.delenv(RESTART_PATH_ENVNAME)

    os.chdir(fmurun_pred)
    fmu_restart = FmuProvider(model="Modelrun", fmu_context=FmuContext.REALIZATION)
    assert "restart_from" not in fmu_restart._metadata["iteration"]


def test_fmuprovider_workflow_reference(fmurun_w_casemetadata):
    """Testing the handling of workflow reference input.

    Metadata definitions of fmu.workflow is that it is a dictionary with 'reference'
    as a mandatory key. In early versions, the 'workflow' argument was to be given as
    a dictionary and directly inserted. However, during development, this has changed
    to a string which is inserted into the 'workflow' element in the outgoing metadata.
    Some users still have legacy workflows that give this as a dictionary, so we will
    continue to allow it, but with a warning.

    This test is asserting that when 'workflow' is given in various shapes and forms,
    it shall always produce valid metadata.

    """
    os.chdir(fmurun_w_casemetadata)

    # workflow input is a string
    myfmu = FmuProvider(workflow="workflow as string")
    assert "workflow" in myfmu._metadata
    assert myfmu._metadata["workflow"] == {"reference": "workflow as string"}

    # workflow input is a correct dict
    with pytest.warns(PendingDeprecationWarning, match="The 'workflow' argument"):
        myfmu = FmuProvider(workflow={"reference": "workflow as dict"})
    assert "workflow" in myfmu._metadata
    assert myfmu._metadata["workflow"] == {"reference": "workflow as dict"}

    # workflow input is non-correct dict
    with pytest.raises(ValueError):
        myfmu = FmuProvider(workflow={"wrong": "workflow as dict"})

    # workflow input is other types - shall fail
    with pytest.raises(TypeError):
        myfmu = FmuProvider(workflow=123.4)
