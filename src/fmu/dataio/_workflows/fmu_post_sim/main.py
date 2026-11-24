"""Upload linked observations and responses via an Ert POST_SIMULATION workflow.

This script is intended to be run through an Ert HOOK POST_SIMULATION workflow.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import ert
import pyarrow.compute as pc

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
from ._config import PostSimulationConfig
from ._observation import ObservationType, get_ert_observations_table
from ._responses import get_ert_responses_table

if TYPE_CHECKING:
    from ert.runpaths import Runpaths as ErtRunpaths
    from ert.storage import Ensemble as ErtEnsemble


# This documentation is compiled into ert's internal docs
POST_SIMULATION_DESCRIPTION = """
WF_FMU_POST_SIMULATION will upload observations and simulated responses from the
active Ert ensemble to Sumo after simulation. Currently supported types are
'summary' and 'rft'. Shared IDs link responses to observations using Ert's
matching rules. It requires existing case metadata from WF_FMU_PRE_SIMULATION and a
<SUMO_CASEPATH> definition in the Ert config.
Responses are uploaded as separate tables per realization; observations are shared.
Note: The workflow should be only run inside FMU Ecosystem after the pre-simulation
workflow has been executed. Don't run this workflow directly from ert configuration.
"""

POST_SIMULATION_EXAMPLES = """
Hook workflow `WF_FMU_POST_SIMULATION` for FMU ECOSYSTEM. 
A typical usage is as follows:

    HOOK_WORKFLOW_JOB xhook_wf_fmu_post WF_FMU_POST_SIMULATION POST_SIMULATION

The workflow takes no arguments. Run WF_FMU_PRE_SIMULATION  as a PRE_SIMULATION
hook first to register the case on Sumo inside the FMU Ecosystem.

Note that ``<SUMO_CASEPATH>`` must be defined in the Ert config for this workflow to
run::

    DEFINE <SUMO_CASEPATH>  <SCRATCH>/<USER>/<CASE_DIR>

"""


def _get_ensemble_name(
    ensemble: ErtEnsemble,
    run_paths: ErtRunpaths,
    casepath: Path,
) -> str:
    """Use the ensemble runpath directory, or iter-0 without an ensemble directory."""
    runpath = Path(
        run_paths.get_paths(realizations=[0], iteration=ensemble.iteration)[0]
    )
    return runpath.name if runpath.parent != casepath else "iter-0"


def _queue_ert_observations(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
    obs_type: ObservationType,
) -> None:
    """Queue an observation table independently of the case workflow."""
    if obs_type == ObservationType.summary:
        standard_result = StandardResultName.observations_summary
        index_columns = ErtObservations.SummaryColumns.index_columns()
    elif obs_type == ObservationType.rft:
        standard_result = StandardResultName.observations_rft
        index_columns = ErtObservations.RftColumns.index_columns()
    else:
        raise ValueError(f"Unsupported post-simulation observation type: {obs_type}")

    table = get_ert_observations_table(ensemble, obs_type)
    if table is None:
        return
    export_config = (
        ExportConfig.builder()
        .content(Content.observations)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=index_columns)
        .file_config(name=standard_result.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .flags(is_observation=True)
        .standard_result(standard_result)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_ert_obs_summary_responses(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export summary responses using fmu-dataio."""
    _queue_ert_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader, ObservationType.summary
    )


def _queue_ert_responses_rft(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export rft responses using fmu-dataio."""
    _queue_ert_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader, ObservationType.rft
    )


def _queue_ert_responses(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: PostSimulationConfig,
    sumo_uploader: SumoUploaderInterface,
    response_type: ObservationType,
) -> None:
    """Queue one uniquely named response table per realization."""
    if response_type == ObservationType.summary:
        content = Content.simulationtimeseries
        standard_result = StandardResultName.responses_summary
        index_columns = ErtObservations.SummaryResponseColumns.index_columns()
    elif response_type == ObservationType.rft:
        content = Content.rft
        standard_result = StandardResultName.responses_rft
        index_columns = ErtObservations.RftResponseColumns.index_columns()
    else:
        raise ValueError(f"Unsupported post-simulation response type: {response_type}")
    table = get_ert_responses_table(ensemble, response_type)
    if table is None:
        return

    for realization in table["realization"].unique():
        realization_table = table.filter(pc.equal(table["realization"], realization))
        export_config = (
            ExportConfig.builder()
            .content(content)
            .access(Classification.internal, rep_include=False)
            .table_config(table_index=index_columns)
            .file_config(
                name=standard_result.value,
                tagname=f"realization-{realization.as_py()}",
            )
            .global_config(workflow_config.global_config)
            .run_context(
                fmu_context=FMUContext.ensemble,
                ensemble_name=ensemble_name,
                casepath=workflow_config.casepath,
            )
            .standard_result(standard_result)
            .build()
        )
        metadata = generate_metadata(export_config, realization_table)
        sumo_uploader.queue_table(realization_table, metadata)


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
    """Upload linked observations and responses from the completed ensemble."""
    ensemble_name = _get_ensemble_name(ensemble, run_paths, workflow_config.casepath)

    for obs_type in (ObservationType.summary, ObservationType.rft):
        _queue_ert_observations(
            ensemble, ensemble_name, workflow_config, sumo_uploader, obs_type
        )

    # Stage every response technology; missing or empty ones stage nothing.
    _queue_ert_obs_summary_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    _queue_ert_responses_rft(ensemble, ensemble_name, workflow_config, sumo_uploader)
    _queue_ert_obs_breakthrough_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    _queue_ert_obs_seismic_responses(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )

    sumo_uploader.upload()


class WfFmuPostSimulation(ert.ErtScript):
    """Upload a finished ensemble's observations and responses to Sumo.

    Ert runs this after the ensemble's simulations complete and passes in that
    ensemble. We read its local storage and link responses using observation IDs.
    """

    stop_on_fail = False

    def run(
        self,
        ensemble: ErtEnsemble,
        run_paths: ErtRunpaths,
    ) -> None:
        """Read and upload the finished ensemble's linked observations and responses."""

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
        cfg = PostSimulationConfig.build_postsim_config(run_paths, casepath)

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
