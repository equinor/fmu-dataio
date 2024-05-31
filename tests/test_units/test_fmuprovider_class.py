"""Test the FmuProvider class applied the _metadata.py module"""

import logging
import os

import fmu.dataio as dataio
import pydantic
import pytest

# from conftest import pretend_ert_env_run1
from fmu.dataio._definitions import FmuContext
from fmu.dataio.exceptions import InvalidMetadataError
from fmu.dataio.providers._fmu import RESTART_PATH_ENVNAME, FmuEnv, FmuProvider

logger = logging.getLogger(__name__)

WORKFLOW = {"reference": "some_work_flow"}
GLOBAL_CONFIG_MODEL = {"name": "Model2", "revision": "22.1.0"}


def test_fmuprovider_no_provider():
    """Testing the FmuProvider where no ERT context is found from env variables."""

    myfmu = FmuProvider(
        model=GLOBAL_CONFIG_MODEL,
        fmu_context=FmuContext.REALIZATION,
        casepath_proposed="",
        workflow=WORKFLOW,
    )
    with pytest.raises(
        InvalidMetadataError, match="Missing casepath or model description"
    ):
        myfmu.get_metadata()


def test_fmuprovider_model_info_in_metadata(fmurun_w_casemetadata):
    """Test that the model info is stored and preserved in the metadata."""

    myfmu = FmuProvider(
        model=GLOBAL_CONFIG_MODEL,
        fmu_context=FmuContext.REALIZATION,
        workflow=WORKFLOW,
    )
    meta = myfmu.get_metadata()
    assert "model" in meta.model_fields_set
    assert meta.model.model_dump(mode="json", exclude_none=True) == GLOBAL_CONFIG_MODEL

    myfmu = FmuProvider(
        model=None,
        fmu_context=FmuContext.REALIZATION,
        workflow=WORKFLOW,
    )

    with pytest.raises(
        InvalidMetadataError, match="Missing casepath or model description"
    ):
        meta = myfmu.get_metadata()


def test_fmuprovider_ert_provider_guess_casemeta_path(fmurun):
    """The casepath input is empty, but try guess from ERT RUNPATH without success.

    Since there are mot metadata here, this will issue a warning
    """
    os.chdir(fmurun)
    with pytest.warns(UserWarning, match="Case metadata does not exist"):
        myfmu = FmuProvider(
            model=GLOBAL_CONFIG_MODEL,
            fmu_context=FmuContext.REALIZATION,
            casepath_proposed="",  # if casepath is undef, try deduce from, _ERT_RUNPATH
            workflow=WORKFLOW,
        )

    assert myfmu.get_casepath() is None
    with pytest.raises(
        InvalidMetadataError, match="Missing casepath or model description"
    ):
        myfmu.get_metadata()


def test_fmuprovider_ert_provider_missing_parameter_txt(fmurun_w_casemetadata):
    """Test for an ERT case, when missing file parameter.txt (e.g. pred. run)"""

    os.chdir(fmurun_w_casemetadata)

    # delete the file for this test
    (fmurun_w_casemetadata / "parameters.txt").unlink()
    myfmu = FmuProvider(
        model=GLOBAL_CONFIG_MODEL,
        fmu_context=FmuContext.REALIZATION,
        workflow=WORKFLOW,
    )
    with pytest.warns(UserWarning, match="parameters.txt file was not found"):
        myfmu.get_metadata()

    assert myfmu._case_name == "ertrun1"
    assert myfmu._real_name == "realization-0"
    assert myfmu._real_id == 0


def test_fmuprovider_arbitrary_iter_name(fmurun_w_casemetadata_pred):
    """Test iteration block is correctly set, also with arbitrary iteration names."""

    os.chdir(fmurun_w_casemetadata_pred)
    myfmu = FmuProvider(
        model=GLOBAL_CONFIG_MODEL,
        fmu_context=FmuContext.REALIZATION,
        workflow=WORKFLOW,
    )
    assert myfmu._case_name == "ertrun1"
    assert myfmu._real_name == "realization-0"
    assert myfmu._real_id == 0
    assert myfmu._iter_name == "pred"
    # iter_id should have the default value
    assert myfmu._iter_id == 0
    meta = myfmu.get_metadata()
    assert str(meta.case.uuid) == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"


def test_fmuprovider_get_real_and_iter_from_env(fmurun_non_equal_real_and_iter):
    """Test that iter and real number is picked up correctly from env"""

    os.chdir(fmurun_non_equal_real_and_iter)
    myfmu = FmuProvider(
        model=GLOBAL_CONFIG_MODEL,
        fmu_context=FmuContext.REALIZATION,
        workflow=WORKFLOW,
    )
    assert myfmu._runpath == fmurun_non_equal_real_and_iter
    assert myfmu._case_name == "ertrun1"
    assert myfmu._real_name == "realization-1"
    assert myfmu._real_id == 1
    assert myfmu._iter_name == "iter-0"
    assert myfmu._iter_id == 0


def test_fmuprovider_no_iter_folder(fmurun_no_iter_folder):
    """Test that the fmuprovider works without a iteration folder"""

    os.chdir(fmurun_no_iter_folder)
    myfmu = FmuProvider(
        model=GLOBAL_CONFIG_MODEL, fmu_context=FmuContext.REALIZATION, workflow=WORKFLOW
    )
    assert myfmu._runpath == fmurun_no_iter_folder
    assert myfmu._casepath == fmurun_no_iter_folder.parent
    assert myfmu._case_name == "ertrun1_no_iter"
    assert myfmu._real_name == "realization-1"
    assert myfmu._real_id == 1
    assert myfmu._iter_name == "iter-0"
    assert myfmu._iter_id == 0

    # also check that it is stored correctly in the metadata
    meta = myfmu.get_metadata()
    assert meta.realization.name == "realization-1"
    assert meta.realization.id == 1
    assert meta.iteration.name == "iter-0"
    assert meta.iteration.id == 0


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
        model=GLOBAL_CONFIG_MODEL,
        fmu_context=FmuContext.CASE,
        workflow=WORKFLOW,
        casepath_proposed=caseroot,
    )

    assert myfmu._case_name == "prehook"
    assert myfmu._real_name == ""


def test_fmuprovider_detect_no_case_metadata(fmurun):
    """Testing the case metadata file which is not found here.

    That will still provide a file path but the metadata will be {} i.e. empty
    """
    os.chdir(fmurun)

    with pytest.warns(UserWarning, match="Case metadata does not exist"):
        myfmu = FmuProvider(
            model=GLOBAL_CONFIG_MODEL,
            fmu_context=FmuContext.REALIZATION,
        )
    with pytest.raises(
        InvalidMetadataError, match="Missing casepath or model description"
    ):
        myfmu.get_metadata()


def test_fmuprovider_case_run(fmurun_prehook):
    """
    When fmu_context="case" and no runpath can be detected from environment
    an error should be raised if no casepath is provided.
    """
    logger.info("Active folder is %s", fmurun_prehook)

    os.chdir(fmurun_prehook)

    # make sure that no runpath environment value is present
    assert FmuEnv.RUNPATH.value is None

    with pytest.warns(UserWarning, match="Could not auto detect the casepath"):
        FmuProvider(
            model=GLOBAL_CONFIG_MODEL,
            fmu_context=FmuContext.CASE,
        )

    # providing the casepath is the solution, and no error is thrown
    myfmu = FmuProvider(
        model=GLOBAL_CONFIG_MODEL,
        fmu_context=FmuContext.CASE,
        casepath_proposed=fmurun_prehook,
    )
    meta = myfmu.get_metadata()
    assert meta.realization is None
    assert myfmu._case_name == fmurun_prehook.name


def test_fmuprovider_valid_restart_env(monkeypatch, fmurun_w_casemetadata, fmurun_pred):
    """Testing the scenario given a valid RESTART_FROM_PATH environment variable

    This shall give the correct restart_from uuid
    """
    os.chdir(fmurun_w_casemetadata)
    fmu_restart_from = FmuProvider(
        model=GLOBAL_CONFIG_MODEL, fmu_context=FmuContext.REALIZATION
    )
    meta_restart_from = fmu_restart_from.get_metadata()

    monkeypatch.setenv(RESTART_PATH_ENVNAME, str(fmurun_w_casemetadata))

    os.chdir(fmurun_pred)
    fmu_restart = FmuProvider(
        model=GLOBAL_CONFIG_MODEL, fmu_context=FmuContext.REALIZATION
    )

    meta_restart = fmu_restart.get_metadata()
    assert meta_restart.iteration.restart_from is not None
    assert meta_restart.iteration.restart_from == meta_restart_from.iteration.uuid


def test_fmuprovider_invalid_restart_env(
    monkeypatch, fmurun_w_casemetadata, fmurun_pred
):
    """Testing the scenario given invalid RESTART_FROM_PATH environment variable

    The iteration metadata will not contain restart_from key
    """
    os.chdir(fmurun_w_casemetadata)

    _ = FmuProvider(model=GLOBAL_CONFIG_MODEL, fmu_context=FmuContext.REALIZATION)

    monkeypatch.setenv(RESTART_PATH_ENVNAME, "/path/to/somewhere/invalid")

    os.chdir(fmurun_pred)
    fmu_restart = FmuProvider(
        model=GLOBAL_CONFIG_MODEL, fmu_context=FmuContext.REALIZATION
    )
    meta = fmu_restart.get_metadata()
    assert meta.iteration.restart_from is None


def test_fmuprovider_no_restart_env(monkeypatch, fmurun_w_casemetadata, fmurun_pred):
    """Testing the scenario without RESTART_FROM_PATH environment variable

    The iteration metadata will not contain restart_from key
    """
    os.chdir(fmurun_w_casemetadata)

    _ = FmuProvider(model=GLOBAL_CONFIG_MODEL, fmu_context=FmuContext.REALIZATION)

    monkeypatch.setenv(RESTART_PATH_ENVNAME, "/path/to/somewhere/invalid")
    monkeypatch.delenv(RESTART_PATH_ENVNAME)

    os.chdir(fmurun_pred)
    restart_meta = FmuProvider(
        model=GLOBAL_CONFIG_MODEL, fmu_context=FmuContext.REALIZATION
    ).get_metadata()
    assert restart_meta.iteration.restart_from is None


def test_fmuprovider_workflow_reference(fmurun_w_casemetadata):
    """Testing the handling of workflow reference input.

    Metadata definitions of fmu.workflow is that it is a dictionary with 'reference'
    as a mandatory key. In early versions, the 'workflow' argument was to be given as
    a dictionary and directly inserted. However, during development, this has changed
    to a string which is inserted into the 'workflow' element in the outgoing metadata.
    Some users still have legacy workflows that give this as a dictionary, so we will
    continue to allow it, but with a warning.
    This test is asserting that when 'workflow' is given in various shapes and forms,
    it shall always produce valid metadata, or give a validation error if not.

    """
    os.chdir(fmurun_w_casemetadata)

    # workflow input is a string
    myfmu_meta = FmuProvider(
        model=GLOBAL_CONFIG_MODEL, workflow="workflow as string"
    ).get_metadata()
    assert myfmu_meta.workflow is not None
    assert myfmu_meta.workflow.model_dump(mode="json") == {
        "reference": "workflow as string"
    }

    # workflow as a dict should give future warning
    with pytest.warns(FutureWarning, match="The 'workflow' argument"):
        dataio.ExportData(workflow={"reference": "workflow as dict"})

    # test that workflow as a dict still gives valid results
    myfmu_meta = FmuProvider(
        model=GLOBAL_CONFIG_MODEL, workflow={"reference": "workflow as dict"}
    ).get_metadata()
    assert myfmu_meta.workflow is not None
    assert myfmu_meta.workflow.model_dump(mode="json") == {
        "reference": "workflow as dict"
    }

    # workflow input is non-correct dict
    with pytest.raises(pydantic.ValidationError):
        FmuProvider(
            model=GLOBAL_CONFIG_MODEL, workflow={"wrong": "workflow as dict"}
        ).get_metadata()

    # workflow input is other types - shall fail
    with pytest.raises(
        pydantic.ValidationError, match="Input should be a valid string"
    ):
        FmuProvider(model=GLOBAL_CONFIG_MODEL, workflow=123.4).get_metadata()
