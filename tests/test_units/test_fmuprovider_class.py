"""Test the FmuProvider class applied the _metadata.py module"""

import importlib
import logging

import pydantic
import pytest
from fmu.datamodels.fmu_results.enums import ErtSimulationMode, FMUContext

from fmu import dataio
from fmu.dataio._runcontext import FmuEnv, RunContext
from fmu.dataio.exceptions import InvalidMetadataError
from fmu.dataio.providers._fmu import (
    DEFAULT_ENSMEBLE_NAME,
    RESTART_PATH_ENVNAME,
    FmuProvider,
)

logger = logging.getLogger(__name__)

WORKFLOW = {"reference": "some_work_flow"}
GLOBAL_CONFIG_MODEL = {"name": "Model2", "revision": "22.1.0"}


def test_fmuprovider_no_provider():
    """Testing the FmuProvider where no ERT context is found from env variables."""
    runcontext = RunContext(casepath_proposed="")

    myfmu = FmuProvider(runcontext=runcontext)
    with pytest.raises(InvalidMetadataError, match="Missing casepath"):
        myfmu.get_metadata()


def test_fmuprovider_model_info_in_metadata(fmurun_w_casemetadata):
    """Test that the model info is stored and preserved in the metadata."""
    runcontext = RunContext()
    myfmu = FmuProvider(
        runcontext,
        model=GLOBAL_CONFIG_MODEL,
    )
    meta = myfmu.get_metadata()
    assert "model" in meta.model_fields_set
    assert meta.model.model_dump(mode="json", exclude_none=True) == GLOBAL_CONFIG_MODEL


def test_fmuprovider_no_model_info_use_case(fmurun_w_casemetadata):
    """Test that if no model info it is picking up from the case metadata."""
    runcontext = RunContext()
    myfmu = FmuProvider(
        runcontext,
        model=None,
        workflow=WORKFLOW,
    )

    meta = myfmu.get_metadata()
    casemeta = myfmu._casemeta
    assert meta.model.name == casemeta.fmu.model.name
    assert meta.model.revision == casemeta.fmu.model.revision


def test_fmuprovider_ert_provider_guess_casemeta_path(
    fmurun, monkeypatch: pytest.MonkeyPatch
):
    """The casepath input is empty, but try guess from ERT RUNPATH without success.

    Since there are mot metadata here, this will issue a warning
    """
    monkeypatch.chdir(fmurun)
    with pytest.warns(UserWarning, match="case metadata"):
        runcontext = RunContext(casepath_proposed="")

    myfmu = FmuProvider(runcontext)

    assert myfmu._casepath is None
    with pytest.raises(InvalidMetadataError, match="Missing casepath"):
        myfmu.get_metadata()


def test_fmuprovider_ert_provider_missing_parameter_txt(
    fmurun_w_casemetadata, monkeypatch: pytest.MonkeyPatch
):
    """Test for an ERT case, when missing file parameter.txt runs ok"""

    runcontext = RunContext()

    # delete the file for this test
    (fmurun_w_casemetadata / "parameters.txt").unlink()
    myfmu = FmuProvider(runcontext)

    assert myfmu._casepath.name == "ertrun1"
    assert myfmu._real_name == "realization-0"
    assert myfmu._real_id == 0


def test_fmuprovider_arbitrary_iter_name(
    fmurun_w_casemetadata_pred, monkeypatch: pytest.MonkeyPatch
):
    """Test iteration block is correctly set, also with arbitrary iteration names."""

    monkeypatch.chdir(fmurun_w_casemetadata_pred)

    runcontext = RunContext()
    myfmu = FmuProvider(runcontext)

    assert myfmu._casepath.name == "ertrun1"
    assert myfmu._real_name == "realization-0"
    assert myfmu._real_id == 0
    assert myfmu._ensemble_name == "pred"
    # iter_id should have the default value
    assert myfmu._ensemble_id == 0
    meta = myfmu.get_metadata()
    assert str(meta.case.uuid) == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"


def test_fmuprovider_get_real_and_iter_from_env(
    fmurun_non_equal_real_and_iter, monkeypatch: pytest.MonkeyPatch
):
    """Test that iter and real number is picked up correctly from env"""
    monkeypatch.chdir(fmurun_non_equal_real_and_iter)

    runcontext = RunContext()
    myfmu = FmuProvider(runcontext)

    assert myfmu._runpath == fmurun_non_equal_real_and_iter
    assert myfmu._casepath.name == "ertrun1"
    assert myfmu._real_name == "realization-1"
    assert myfmu._real_id == 1
    assert myfmu._ensemble_name == "iter-0"
    assert myfmu._ensemble_id == 0


def test_fmuprovider_no_iter_folder(
    fmurun_no_iter_folder, monkeypatch: pytest.MonkeyPatch
):
    """Test that the fmuprovider works without a iteration folder"""

    monkeypatch.chdir(fmurun_no_iter_folder)

    runcontext = RunContext()
    myfmu = FmuProvider(runcontext)

    assert myfmu._runpath == fmurun_no_iter_folder
    assert myfmu._casepath == fmurun_no_iter_folder.parent
    assert myfmu._casepath.name == "ertrun1_no_iter"
    assert myfmu._real_name == "realization-1"
    assert myfmu._real_id == 1
    assert myfmu._ensemble_name == "iter-0"
    assert myfmu._ensemble_id == 0

    # also check that it is stored correctly in the metadata
    meta = myfmu.get_metadata()
    assert meta.realization.name == "realization-1"
    assert meta.realization.id == 1
    assert meta.iteration.name == "iter-0"
    assert meta.iteration.id == 0


def test_fmuprovider_prehook_case(
    tmp_path, globalconfig2, fmurun_prehook, monkeypatch: pytest.MonkeyPatch
):
    """The fmu run case metadata is created with Create case; then get provider.

    A typical prehook section in a ERT run is to establish case metadata, and then
    subsequent hook workflows should still recognize this as an ERT run, altough
    no iter and realization folders exists. This requires fmu_contact=case* and that
    key casepath_proposed is given explicitly!.

    I *may* be that this behaviour can be removed in near future, since the ERT env
    variables now will tell us that this is an active ERT run.
    """
    caseroot = tmp_path / "prehook"
    caseroot.mkdir(parents=True)
    monkeypatch.chdir(caseroot)

    icase = dataio.CreateCaseMetadata(
        config=globalconfig2,
        rootfolder=caseroot,
        casename="MyCaseName",
    )
    exp = icase.export()

    casemetafile = caseroot / "share/metadata/fmu_case.yml"

    assert casemetafile.is_file()
    assert exp == str(casemetafile.resolve())

    monkeypatch.chdir(fmurun_prehook)
    logger.debug("Case root proposed is: %s", caseroot)
    runcontext = RunContext(casepath_proposed=caseroot, fmu_context=FMUContext.case)
    myfmu = FmuProvider(runcontext)

    assert myfmu._casepath.name == "prehook"
    assert myfmu._real_name == ""


def test_fmuprovider_detect_no_case_metadata(fmurun, monkeypatch: pytest.MonkeyPatch):
    """Testing the case metadata file which is not found here.

    That will still provide a file path but the metadata will be {} i.e. empty
    """
    monkeypatch.chdir(fmurun)

    with pytest.warns(UserWarning, match="case metadata"):
        runcontext = RunContext()
        myfmu = FmuProvider(runcontext)
    with pytest.raises(InvalidMetadataError, match="Missing casepath"):
        myfmu.get_metadata()


def test_fmuprovider_case_run(fmurun_prehook, monkeypatch: pytest.MonkeyPatch):
    """
    When fmu_context="case" and no runpath can be detected from environment
    an error should be raised if no casepath is provided.
    """
    logger.info("Active folder is %s", fmurun_prehook)

    monkeypatch.chdir(fmurun_prehook)

    # make sure that no runpath environment value is present
    assert FmuEnv.RUNPATH.value is None

    with pytest.warns(UserWarning, match="Could not auto detect the case metadata"):
        runcontext = RunContext(fmu_context=FMUContext.case)
        FmuProvider(runcontext)

    # providing the casepath is the solution, and no error is thrown
    runcontext = RunContext(
        fmu_context=FMUContext.case, casepath_proposed=fmurun_prehook
    )
    myfmu = FmuProvider(runcontext)
    meta = myfmu.get_metadata()
    assert meta.realization is None
    assert myfmu._casepath.name == fmurun_prehook.name


def test_fmuprovider_valid_restart_env(
    monkeypatch: pytest.MonkeyPatch, fmurun_w_casemetadata, fmurun_pred
):
    """Testing the scenario given a valid RESTART_FROM_PATH environment variable

    This shall give the correct restart_from uuid
    """
    runcontext = RunContext()
    fmu_restart_from = FmuProvider(runcontext)
    meta_restart_from = fmu_restart_from.get_metadata()

    monkeypatch.setenv(RESTART_PATH_ENVNAME, str(fmurun_w_casemetadata))

    monkeypatch.chdir(fmurun_pred)
    runcontext = RunContext()
    fmu_restart = FmuProvider(runcontext)

    meta_restart = fmu_restart.get_metadata()
    assert meta_restart.iteration.restart_from is not None
    assert meta_restart.iteration.restart_from == meta_restart_from.iteration.uuid


def test_fmuprovider_valid_relative_restart_env(
    monkeypatch: pytest.MonkeyPatch, fmurun_w_casemetadata, fmurun_pred
):
    """
    Test giving a valid RESTART_FROM_PATH environment variable that contains
    a relative path from the existing runpath, which is a common use case.
    """
    runcontext = RunContext()
    meta_restart_from = FmuProvider(runcontext).get_metadata()

    # using a relative path as input
    monkeypatch.setenv(RESTART_PATH_ENVNAME, "../iter-0")

    monkeypatch.chdir(fmurun_pred)
    runcontext = RunContext()
    meta_restart = FmuProvider(runcontext).get_metadata()

    assert meta_restart.iteration.restart_from is not None
    assert meta_restart.iteration.restart_from == meta_restart_from.iteration.uuid


def test_fmuprovider_restart_env_no_iter_folder(
    monkeypatch, fmurun_no_iter_folder, fmurun_pred
):
    """
    Test giving a valid RESTART_FROM_PATH environment variable
    for a fmu run without iteration folders
    """
    monkeypatch.chdir(fmurun_no_iter_folder)
    runcontext = RunContext()
    meta_restart_from = FmuProvider(runcontext).get_metadata()
    assert meta_restart_from.iteration.name == DEFAULT_ENSMEBLE_NAME

    # using a relative path as input
    monkeypatch.setenv(RESTART_PATH_ENVNAME, str(fmurun_no_iter_folder))

    monkeypatch.chdir(fmurun_pred)
    runcontext = RunContext()
    meta_restart = FmuProvider(runcontext).get_metadata()
    assert meta_restart.iteration.restart_from is not None
    assert meta_restart.iteration.restart_from == meta_restart_from.iteration.uuid


def test_fmuprovider_invalid_restart_env(
    monkeypatch: pytest.MonkeyPatch, fmurun_w_casemetadata, fmurun_pred
):
    """Testing the scenario given invalid RESTART_FROM_PATH environment variable

    The iteration metadata will not contain restart_from key
    """

    runcontext = RunContext()
    _ = FmuProvider(runcontext)

    monkeypatch.setenv(RESTART_PATH_ENVNAME, "/path/to/somewhere/invalid")

    monkeypatch.chdir(fmurun_pred)
    with pytest.warns(UserWarning, match="non existing"):
        runcontext = RunContext()
        meta = FmuProvider(runcontext).get_metadata()
    assert meta.iteration.restart_from is None


def test_fmuprovider_no_restart_env(
    monkeypatch: pytest.MonkeyPatch, fmurun_w_casemetadata, fmurun_pred
):
    """Testing the scenario without RESTART_FROM_PATH environment variable

    The iteration metadata will not contain restart_from key
    """

    runcontext = RunContext()
    _ = FmuProvider(runcontext)

    monkeypatch.setenv(RESTART_PATH_ENVNAME, "/path/to/somewhere/invalid")
    monkeypatch.delenv(RESTART_PATH_ENVNAME)

    monkeypatch.chdir(fmurun_pred)
    runcontext = RunContext()
    restart_meta = FmuProvider(runcontext).get_metadata()
    assert restart_meta.iteration.restart_from is None


def test_fmuprovider_workflow_reference(
    fmurun_w_casemetadata, globalconfig2, monkeypatch: pytest.MonkeyPatch
):
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

    # workflow input is a string
    runcontext = RunContext()
    myfmu_meta = FmuProvider(
        runcontext,
        workflow="workflow as string",
    ).get_metadata()
    assert myfmu_meta.workflow is not None
    assert myfmu_meta.workflow.model_dump(mode="json") == {
        "reference": "workflow as string"
    }

    # workflow as a dict should give future warning
    with pytest.warns(FutureWarning, match="The 'workflow' argument"):
        dataio.ExportData(
            config=globalconfig2, workflow={"reference": "workflow as dict"}
        )

    # test that workflow as a dict still gives valid results
    myfmu_meta = FmuProvider(
        runcontext,
        workflow={"reference": "workflow as dict"},
    ).get_metadata()

    assert myfmu_meta.workflow is not None
    assert myfmu_meta.workflow.model_dump(mode="json") == {
        "reference": "workflow as dict"
    }

    # workflow input is non-correct dict
    with pytest.raises(pydantic.ValidationError):
        FmuProvider(
            runcontext,
            workflow={"wrong": "workflow as dict"},
        ).get_metadata()

    # workflow input is other types - shall fail
    with pytest.raises(
        pydantic.ValidationError, match="Input should be a valid string"
    ):
        FmuProvider(
            runcontext,
            workflow=123.4,
        ).get_metadata()


def test_ert_simulation_modes_one_to_one() -> None:
    """Ensure dataio known modes match those defined by Ert.

    These are currently defined in `ert.mode_definitions`.

    - `MODULE_MODE` is skipped due to seemingly being relevant to Ert internally.
      The modes are duplicated there.
    """
    ert_mode_definitions = importlib.import_module("ert.mode_definitions")
    ert_modes = {
        getattr(ert_mode_definitions, name)
        for name in dir(ert_mode_definitions)
        if not name.startswith("__")
        and name != "MODULE_MODE"
        and isinstance(getattr(ert_mode_definitions, name), str)
    }
    dataio_known_modes = {mode.value for mode in ErtSimulationMode}

    assert ert_modes == dataio_known_modes
