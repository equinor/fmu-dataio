from __future__ import annotations

import ert
from ert.plugins.plugin_manager import ErtPluginManager
from packaging.version import Version

import fmu.dataio._workflows.jobs
from fmu.dataio._workflows import copy_preprocessed
from fmu.dataio._workflows.case import main as create_case_metadata
from fmu.dataio._workflows.fmu_post_sim import main as fmu_post_sim


def test_hook_implementations() -> None:
    plugin_manager = ErtPluginManager(
        plugins=[
            fmu.dataio._workflows.jobs,
            create_case_metadata,
            copy_preprocessed,
            fmu_post_sim,
        ]
    )

    expected_forward_models: set[str] = set()
    if Version("0.0.0") < Version(ert.shared.__version__) < Version("17.0.0"):
        installable_fms = plugin_manager.get_installable_jobs()
    else:
        installable_fms = plugin_manager.forward_model_steps
    assert set(installable_fms) == expected_forward_models

    expected_workflow_jobs = {
        "WF_CREATE_CASE_METADATA",
        "WF_COPY_PREPROCESSED_DATAIO",
        "WF_FMU_POST_SIMULATION",
    }
    installable_workflow_jobs = plugin_manager.get_ertscript_workflows().get_workflows()
    for wf_name, _ in installable_workflow_jobs.items():
        assert wf_name in expected_workflow_jobs

    assert set(installable_workflow_jobs) == expected_workflow_jobs


def test_hook_implementations_docs() -> None:
    plugin_manager = ErtPluginManager(
        plugins=[
            fmu.dataio._workflows.jobs,
            create_case_metadata,
            copy_preprocessed,
            fmu_post_sim,
        ]
    )

    if Version("0.0.0") < Version(ert.shared.__version__) < Version("17.0.0"):
        installable_fms = plugin_manager.get_installable_jobs()
        fm_docs = plugin_manager.get_documentation_for_jobs()
    else:
        installable_fms = plugin_manager.forward_model_steps
        fm_docs = plugin_manager.get_documentation_for_forward_model_steps()

    assert set(fm_docs) == set(installable_fms)

    for fm_name in installable_fms:
        assert fm_docs[fm_name]["description"] != ""
        assert fm_docs[fm_name]["examples"] != ""
        assert fm_docs[fm_name]["category"] != "other"

    installable_workflow_jobs = plugin_manager.get_ertscript_workflows().get_workflows()
    wf_docs = plugin_manager.get_documentation_for_workflows()
    assert set(wf_docs) == set(installable_workflow_jobs)
    for wf_name in installable_workflow_jobs:
        assert wf_docs[wf_name]["description"] != ""
        assert wf_docs[wf_name]["examples"] != ""
        assert wf_docs[wf_name]["category"] != "other"


def test_modules_register_their_workflows() -> None:
    case_workflows = (
        ErtPluginManager(plugins=[create_case_metadata])
        .get_ertscript_workflows()
        .get_workflows()
    )
    assert set(case_workflows) == {"WF_CREATE_CASE_METADATA"}

    post_sim_workflows = (
        ErtPluginManager(plugins=[fmu_post_sim])
        .get_ertscript_workflows()
        .get_workflows()
    )
    assert set(post_sim_workflows) == {"WF_FMU_POST_SIMULATION"}

    wf_docs = ErtPluginManager(
        plugins=[create_case_metadata, fmu_post_sim]
    ).get_documentation_for_workflows()
    for workflow_name in ("WF_CREATE_CASE_METADATA", "WF_FMU_POST_SIMULATION"):
        assert wf_docs[workflow_name]["description"] != ""
        assert wf_docs[workflow_name]["examples"] != ""
        assert wf_docs[workflow_name]["category"] != "other"
