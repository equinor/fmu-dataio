"""Test the _MetaData class from the _metadata.py module"""
import os

import fmu.dataio as dio
import pytest
from fmu.dataio._fmu_provider import RESTART_PATH_ENVNAME, _FmuProvider, _get_folderlist

FOLDERTREE = "scratch/myfield/case/realization-13/iter-2"


def test_get_folderlist(fmurun):
    os.chdir(fmurun)
    mylist = _get_folderlist(fmurun)
    assert mylist[-1] == "iter-0"
    assert mylist[-3] == "ertrun1"


def test_fmuprovider_no_provider(testroot, globalconfig1):
    """Testing the FmuProvider basics where no ERT context is found from folder tree."""
    os.chdir(testroot)

    ex = dio.ExportData(
        fmu_context="realization", config=globalconfig1, content="depth"
    )
    myfmu = _FmuProvider(ex)
    myfmu.detect_provider()

    assert myfmu.is_fmurun is False
    assert myfmu.case_name is None


def test_fmuprovider_ert2_provider(fmurun, globalconfig1):
    """Testing the FmuProvider for an ERT2 case; case metadata are missing here"""
    os.chdir(fmurun)

    ex = dio.ExportData(
        fmu_context="realization", config=globalconfig1, content="depth"
    )
    ex._rootpath = fmurun

    myfmu = _FmuProvider(ex)
    with pytest.warns(UserWarning, match="ERT2 is found but no case metadata"):
        # since case name is missing
        myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0


def test_fmuprovider_ert2_provider_missing_parameter_txt(fmurun, globalconfig1):
    """Test for an ERT2 case, when missing file parameter.txt (e.g. pred. run)"""

    os.chdir(fmurun)
    (fmurun / "parameters.txt").unlink()

    ex = dio.ExportData(
        fmu_context="realization", content="depth", config=globalconfig1
    )
    ex._rootpath = fmurun

    myfmu = _FmuProvider(ex)
    with pytest.warns(UserWarning, match="ERT2 is found but no case metadata"):
        myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0


def test_fmuprovider_arbitrary_iter_name(edataobj1, fmurun_w_casemetadata_pred):
    """Test that iteration block correctly populated also with arbitrary iteration
    names."""

    edataobj1._rootpath = fmurun_w_casemetadata_pred
    os.chdir(fmurun_w_casemetadata_pred)
    myfmu = _FmuProvider(edataobj1)
    myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0
    assert myfmu.iter_name == "pred"
    assert myfmu.iter_id is None
    assert "fmu_case" in str(myfmu.case_metafile)
    assert (
        myfmu.case_metadata["fmu"]["case"]["uuid"]
        == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"
    )


def test_fmuprovider_prehook_case(globalconfig2, tmp_path):
    """The fmu run case metadata is initialized with Initialize case; then fet provider.

    A typical prehook section in a ERT2 run is to establish case metadata, and then
    subsequent hook workflows should still recognize this as an ERT2 run, altough
    no iter and realization folders exists. This requires fmu_contact=case* and that
    key casepath is given explicitly!.
    """

    icase = dio.InitializeCase(config=globalconfig2)

    caseroot = tmp_path / "prehook"
    caseroot.mkdir(parents=True)

    os.chdir(caseroot)

    exp = icase.export(
        rootfolder=caseroot,
        casename="MyCaseName",
        caseuser="MyUser",
        description="Some description",
    )
    casemetafile = caseroot / "share/metadata/fmu_case.yml"
    assert casemetafile.is_file()
    assert exp == str(casemetafile.resolve())

    eobj = dio.ExportData(
        config=globalconfig2,
        name="TopWhatever",
        content="depth",
        tagname="mytag",
        is_observation=True,
        fmu_context="case",
        casepath=caseroot,
    )

    myfmu = _FmuProvider(eobj)
    myfmu.detect_provider()
    assert myfmu.case_name == "prehook"
    assert myfmu.real_name is None


def test_fmuprovider_detect_no_case_metadata(fmurun, edataobj1):
    """Testing the case metadata file which is not found here.

    That will still provide a file path but the metadata will be {} i.e. empty
    """
    os.chdir(fmurun)
    edataobj1._rootpath = fmurun

    myfmu = _FmuProvider(edataobj1)
    with pytest.warns(UserWarning, match="ERT2 is found but no case metadata"):
        myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0
    assert "fmu_case" in str(myfmu.case_metafile)
    assert not myfmu.case_metadata


def test_fmuprovider_valid_restart_env(fmurun_w_casemetadata, fmurun_pred, edataobj1):
    """Testing the scenario given a valid RESTART_FROM_PATH environment variable

    This will give the correct restart_from uuid
    """

    edataobj1._rootpath = fmurun_w_casemetadata
    os.chdir(fmurun_w_casemetadata)
    fmu_restart_from = _FmuProvider(edataobj1)
    fmu_restart_from.detect_provider()

    os.environ[RESTART_PATH_ENVNAME] = str(fmurun_w_casemetadata)
    edataobj1._rootpath = fmurun_pred
    os.chdir(fmurun_pred)
    fmu_restart = _FmuProvider(edataobj1)
    with pytest.warns(UserWarning, match="ERT2 is found but no case metadata"):
        fmu_restart.detect_provider()
    assert (
        fmu_restart.metadata["iteration"]["restart_from"]
        == fmu_restart_from.metadata["iteration"]["uuid"]
    )


def test_fmuprovider_invalid_restart_env(fmurun_w_casemetadata, fmurun_pred, edataobj1):
    """Testing the scenario given invalid RESTART_FROM_PATH environment variable

    The iteration metadata will not contain restart_from key
    """

    edataobj1._rootpath = fmurun_w_casemetadata
    os.chdir(fmurun_w_casemetadata)
    fmu_restart_from = _FmuProvider(edataobj1)
    fmu_restart_from.detect_provider()

    os.environ[RESTART_PATH_ENVNAME] = "/path/to/somewhere/invalid"
    edataobj1._rootpath = fmurun_pred
    os.chdir(fmurun_pred)
    fmu_restart = _FmuProvider(edataobj1)
    with pytest.warns(UserWarning, match="ERT2 is found but no case metadata"):
        fmu_restart.detect_provider()
    assert "restart_from" not in fmu_restart.metadata["iteration"]


def test_fmuprovider_no_restart_env(fmurun_w_casemetadata, fmurun_pred, edataobj1):
    """Testing the scenario without RESTART_FROM_PATH environment variable

    The iteration metadata will not contain restart_from key
    """

    edataobj1._rootpath = fmurun_w_casemetadata
    os.chdir(fmurun_w_casemetadata)
    fmu_restart_from = _FmuProvider(edataobj1)
    fmu_restart_from.detect_provider()

    edataobj1._rootpath = fmurun_pred
    os.chdir(fmurun_pred)
    fmu_restart = _FmuProvider(edataobj1)
    with pytest.warns(UserWarning, match="ERT2 is found but no case metadata"):
        fmu_restart.detect_provider()
    assert "restart_from" not in fmu_restart.metadata["iteration"]


def test_fmuprovider_detect_case_has_metadata(fmurun_w_casemetadata, edataobj1):
    """Testing the case metadata file which is found here"""
    edataobj1._rootpath = fmurun_w_casemetadata
    os.chdir(fmurun_w_casemetadata)
    myfmu = _FmuProvider(edataobj1)
    myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0
    assert "fmu_case" in str(myfmu.case_metafile)
    assert (
        myfmu.case_metadata["fmu"]["case"]["uuid"]
        == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"
    )


def test_fmuprovider_workflow_reference(fmurun_w_casemetadata, edataobj1):
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
    edataobj1._rootpath = fmurun_w_casemetadata
    os.chdir(fmurun_w_casemetadata)

    # workflow input is a string
    edataobj1.workflow = "my workflow"
    myfmu = _FmuProvider(edataobj1)
    myfmu.detect_provider()
    assert "workflow" in myfmu.metadata
    assert myfmu.metadata["workflow"] == {"reference": "my workflow"}

    # workflow input is a correct dict
    edataobj1.workflow = {"reference": "my workflow"}
    myfmu = _FmuProvider(edataobj1)
    with pytest.warns(PendingDeprecationWarning, match="The 'workflow' argument"):
        myfmu.detect_provider()
    assert "workflow" in myfmu.metadata
    assert myfmu.metadata["workflow"] == {"reference": "my workflow"}

    # workflow input is non-correct dict
    edataobj1.workflow = {"something": "something"}
    myfmu = _FmuProvider(edataobj1)
    with pytest.raises(ValueError):
        myfmu.detect_provider()

    # workflow input is other types - shall fail
    edataobj1.workflow = 123.4
    myfmu = _FmuProvider(edataobj1)
    with pytest.raises(TypeError):
        myfmu.detect_provider()
