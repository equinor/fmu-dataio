"""Upload simulated responses to Sumo via an Ert POST_SIMULATION workflow.

This script is intended to be run through an Ert HOOK POST_SIMULATION workflow.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import ert

from fmu.dataio._export import ExportConfig
from fmu.dataio._interfaces import SumoUploaderInterface
from fmu.dataio._metadata import generate_metadata
from fmu.dataio._runcontext import RunContext
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import Content, FMUContext
from fmu.datamodels.standard_results.enums import (
    ErtObservations,
    StandardResultName,
)

from .._utils import validate_casepath
from ..case._observations import ObservationType
from ..case.main import _get_ensemble_name
from ._config import PostSimulationConfig, build_postsim_config
from ._responses import get_ert_responses_table

if TYPE_CHECKING:
    from ert.runpaths import Runpaths as ErtRunpaths
    from ert.storage import Ensemble as ErtEnsemble


# This documentation is compiled into ert's internal docs
POST_SIMULATION_DESCRIPTION = """
WF_FMU_POST_SIMULATION will upload simulated responses from the active Ert ensemble
to Sumo after simulation. Currently supported response types are 'summary' and
'rft'. It requires existing case metadata from WF_CREATE_CASE_METADATA and a
<SUMO_CASEPATH> definition in the Ert config.
"""

POST_SIMULATION_EXAMPLES = """
Hook the ``WF_FMU_POST_SIMULATION`` workflow job directly as a POST_SIMULATION
hook in your Ert config. No separate workflow file is needed::

    HOOK_WORKFLOW_JOB xhook_wf_fmu_post WF_FMU_POST_SIMULATION POST_SIMULATION

The workflow takes no arguments. Run WF_CREATE_CASE_METADATA  as a PRE_SIMULATION
hook first to register the case on Sumo.

Note that ``<SUMO_CASEPATH>`` must be defined in the Ert config for this workflow to
run::

    DEFINE <SUMO_CASEPATH>  <SCRATCH>/<USER>/<CASE_DIR>

"""


def _queue_ert_obs_summary_responses(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export summary responses using fmu-dataio."""
    table = get_ert_responses_table(ensemble, ObservationType.summary)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.simulationtimeseries)
        .access(Classification.internal, rep_include=False)
        .table_config(
            table_index=ErtObservations.SummaryResponseColumns.index_columns()
        )
        .file_config(name=StandardResultName.responses_summary.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .standard_result(StandardResultName.responses_summary)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_ert_obs_rft_responses(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export rft responses using fmu-dataio."""
    table = get_ert_responses_table(ensemble, ObservationType.rft)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.rft)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=ErtObservations.RftResponseColumns.index_columns())
        .file_config(name=StandardResultName.responses_rft.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .standard_result(StandardResultName.responses_rft)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_ert_obs_breakthrough_responses(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export breakthrough responses using fmu-dataio."""
    # TODO: Breakthrough responses are temporarily excluded from Sumo upload.


def _queue_ert_obs_seismic_responses(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export seismic responses using fmu-dataio."""
    # TODO: Seismic responses are temporarily excluded from Sumo upload.


def _upload_ert_observations_responses(
    ensemble: ErtEnsemble,
    run_paths: ErtRunpaths,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Upload simulated responses from the completed ensemble to Sumo."""
    ensemble_name = _get_ensemble_name(ensemble, run_paths, workflow_config.casepath)

    # Stage every response technology; missing or empty ones stage nothing.
    _queue_ert_obs_summary_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    _queue_ert_obs_rft_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    _queue_ert_obs_breakthrough_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    _queue_ert_obs_seismic_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )

    sumo_uploader.upload()


class WfFmuPostSimulation(ert.ErtScript):
    """Upload a finished ensemble's simulated responses via an Ert POST_SIMULATION hook.

    Ert runs this after the ensemble's simulations complete and passes in that
    ensemble. We read its responses from local storage and upload them to Sumo.
    """

    stop_on_fail = False

    def run(
        self,
        ensemble: ErtEnsemble,
        run_paths: ErtRunpaths,
    ) -> None:
        """Read the finished ensemble's responses from storage and upload them."""

        sumo_casepath = run_paths.substitutions.get("<SUMO_CASEPATH>")
        if not sumo_casepath:
            raise ValueError("Define <SUMO_CASEPATH> in the Ert config")

        casepath = validate_casepath(Path(sumo_casepath))

        # The case must already be registered by the PRE_SIMULATION hook, because
        # we reuse its uuid to upload into the same Sumo case.
        case_metadata = RunContext(
            casepath_proposed=casepath, fmu_context=FMUContext.ensemble
        ).case_metadata
        if case_metadata is None:
            raise ValueError(
                "Missing case metadata. Run WF_CREATE_CASE_METADATA "
                "as a PRE_SIMULATION hook first."
            )

        # Resolve casepath + global config
        cfg = build_postsim_config(run_paths, casepath)

        # Attach to the existing Sumo case via its uuid instead of creating a new one.
        sumo_uploader = SumoUploaderInterface(
            env=os.environ.get("SUMO_ENV", "prod"),
            case_uuid=str(case_metadata.fmu.case.uuid),
        )

        _upload_ert_observations_responses(
            ensemble=ensemble,
            run_paths=run_paths,
            workflow_config=cfg,
            sumo_uploader=sumo_uploader,
        )


@ert.plugin(name="fmu_dataio")
def ertscript_workflow(config: ert.WorkflowConfigs) -> None:
    """Hook the post-simulation workflow into ERT."""

    config.add_workflow(
        WfFmuPostSimulation,
        "WF_FMU_POST_SIMULATION",
        description=POST_SIMULATION_DESCRIPTION,
        examples=POST_SIMULATION_EXAMPLES,
        category="export",
    )
