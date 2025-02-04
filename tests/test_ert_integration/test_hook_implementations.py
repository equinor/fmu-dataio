import os

from ert.plugins.plugin_manager import ErtPluginManager

import fmu.dataio.hook_implementations.jobs
from fmu.dataio.scripts import copy_preprocessed, create_case_metadata


def test_hook_implementations():
    plugin_manager = ErtPluginManager(
        plugins=[
            fmu.dataio.hook_implementations.jobs,
            create_case_metadata,
            copy_preprocessed,
        ]
    )

    expected_forward_models = set()
    installable_fms = plugin_manager.get_installable_jobs()
    assert set(installable_fms) == expected_forward_models

    expected_workflow_jobs = {"WF_CREATE_CASE_METADATA", "WF_COPY_PREPROCESSED_DATAIO"}
    installable_workflow_jobs = plugin_manager.get_installable_workflow_jobs()
    for wf_name, wf_location in installable_workflow_jobs.items():
        assert wf_name in expected_workflow_jobs
        assert os.path.isfile(wf_location)

    assert set(installable_workflow_jobs) == expected_workflow_jobs


def test_hook_implementations_docs():
    plugin_manager = ErtPluginManager(
        plugins=[
            fmu.dataio.hook_implementations.jobs,
            create_case_metadata,
            copy_preprocessed,
        ]
    )

    installable_fms = plugin_manager.get_installable_jobs()
    fm_docs = plugin_manager.get_documentation_for_jobs()
    assert set(fm_docs) == set(installable_fms)
    for fm_name in installable_fms:
        assert fm_docs[fm_name]["description"] != ""
        assert fm_docs[fm_name]["examples"] != ""
        assert fm_docs[fm_name]["category"] != "other"

    installable_workflow_jobs = plugin_manager.get_installable_workflow_jobs()
    wf_docs = plugin_manager.get_documentation_for_workflows()
    assert set(wf_docs) == set(installable_workflow_jobs)
    for wf_name in installable_workflow_jobs:
        assert wf_docs[wf_name]["description"] != ""
        assert wf_docs[wf_name]["examples"] != ""
        assert wf_docs[wf_name]["category"] != "other"
