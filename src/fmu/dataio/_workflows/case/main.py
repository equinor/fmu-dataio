"""Create FMU case metadata and register case on Sumo (optional).

This script is intended to be run through an Ert HOOK PRE_SIMULATION workflow.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

import ert
from ert.config import ConfigWarning

from fmu.dataio._export import ExportConfig
from fmu.dataio._interfaces import SumoUploaderInterface
from fmu.dataio._metadata import generate_metadata
from fmu.dataio._workflows.fmu_pre_sim.export_case_metadata import (
    ExportCaseMetadata,
)
from fmu.dataio._workflows.fmu_pre_sim.main import (
    _copy_fmu_directory,
    _get_ensemble_name,
    _upload_files_to_sumo,
)
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import Content, FMUContext
from fmu.datamodels.standard_results.enums import ErtObservations, StandardResultName

from .._utils import resolve_casepath
from ._config import CaseWorkflowConfig
from ._observations import ObservationType, get_ert_observations_table

if TYPE_CHECKING:
    from typing import Any

    from ert.runpaths import Runpaths as ErtRunpaths
    from ert.storage import Ensemble as ErtEnsemble


logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

DEPRECATION_MESSAGE = (
    "The WF_CREATE_CASE_METADATA workflow is deprecated and will be removed in a "
    "future version of fmu-dataio. Remove WF_CREATE_CASE_METADATA from your Ert "
    "configuration and use FMU Ecosystem instead. FMU Ecosystem manages the "
    "replacement workflow, WF_FMU_PRE_SIMULATION, which registers the case in Sumo. "
    "Do not add WF_FMU_PRE_SIMULATION to your Ert configuration manually."
)

# This documentation is compiled into ert's internal docs
DESCRIPTION = """
**Deprecated:** ``WF_CREATE_CASE_METADATA`` will be removed in a future version of
fmu-dataio.

Remove ``WF_CREATE_CASE_METADATA`` from your Ert configuration and use FMU Ecosystem
instead. FMU Ecosystem manages the replacement workflow, ``WF_FMU_PRE_SIMULATION``,
which registers the case in Sumo. Do not add ``WF_FMU_PRE_SIMULATION`` to your Ert
configuration manually.
"""

EXAMPLES = """
**Migration:** Remove the workflow entry that invokes ``WF_CREATE_CASE_METADATA``
and its associated ``LOAD_WORKFLOW`` and ``HOOK_WORKFLOW`` entries from your Ert
configuration. Use FMU Ecosystem to manage case registration in Sumo..

Legacy usage: create an Ert workflow e.g. called
``ert/bin/workflows/xhook_create_case_metadata`` with::

    WF_CREATE_CASE_METADATA "--sumo"

Arguments:
    --sumo: Register case on Sumo

Note that ``<SUMO_CASEPATH>`` must be defined in the Ert config for this workflow to run::

    DEFINE <SUMO_CASEPATH>  <SCRATCH>/<USER>/<CASE_DIR>

"""  # noqa: E501


def _queue_ert_observations_breakthrough(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export breakthrough observation table using fmu-dataio."""

    table = get_ert_observations_table(ensemble, ObservationType.breakthrough)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.observations)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=ErtObservations.BreakthroughColumns.index_columns())
        .file_config(name=StandardResultName.observations_breakthrough.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .flags(is_observation=True)
        .standard_result(StandardResultName.observations_breakthrough)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_ert_observations_rft(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export rft observation table using fmu-dataio."""
    table = get_ert_observations_table(ensemble, ObservationType.rft)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.observations)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=ErtObservations.RftColumns.index_columns())
        .file_config(name=StandardResultName.observations_rft.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .flags(is_observation=True)
        .standard_result(StandardResultName.observations_rft)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_ert_observations_summary(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export summary observation table using fmu-dataio."""

    table = get_ert_observations_table(ensemble, ObservationType.summary)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.observations)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=ErtObservations.SummaryColumns.index_columns())
        .file_config(name=StandardResultName.observations_summary.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .flags(is_observation=True)
        .standard_result(StandardResultName.observations_summary)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_ert_observations_seismic(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export seismic observation table using fmu-dataio."""
    table = get_ert_observations_table(ensemble, ObservationType.seismic)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.observations)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=ErtObservations.SeismicColumns.index_columns())
        .file_config(name=StandardResultName.observations_seismic.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .flags(is_observation=True)
        .standard_result(StandardResultName.observations_seismic)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_ert_observations(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Queue all Ert observation tables for upload to Sumo.

    Observation upload is kept in the legacy workflow only. The replacement
    WF_FMU_PRE_SIMULATION workflow does not upload observations; a dedicated
    post-simulation workflow will upload observations and responses together.
    """
    _queue_ert_observations_rft(ensemble, ensemble_name, workflow_config, sumo_uploader)
    _queue_ert_observations_summary(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    _queue_ert_observations_breakthrough(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    _queue_ert_observations_seismic(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )


def _run_workflow(
    ensemble: ErtEnsemble,
    run_paths: ErtRunpaths,
    workflow_config: CaseWorkflowConfig,
) -> None:
    """Main workflow entry point."""
    logger.setLevel(workflow_config.verbosity)

    case_metadata_path = ExportCaseMetadata.from_workflow_config(
        workflow_config
    ).export()
    logger.debug(f"Case metadata exported to {case_metadata_path}")

    if workflow_config.register_on_sumo:
        sumo_uploader = SumoUploaderInterface.from_new_case(Path(case_metadata_path))
        ensemble_name = _get_ensemble_name(
            ensemble, run_paths, workflow_config.casepath
        )
        # Queue observations first; the shared pre-sim upload queues parameters and
        # .fmu tables and then uploads everything queued in one batch.
        _queue_ert_observations(ensemble, ensemble_name, workflow_config, sumo_uploader)
        _upload_files_to_sumo(
            ensemble=ensemble,
            run_paths=run_paths,
            workflow_config=workflow_config,
            sumo_uploader=sumo_uploader,
        )


def get_parser() -> argparse.ArgumentParser:
    """Construct parser object."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "casepath",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "Absolute path to the case. If not provided, "
            "it is resolved from the <SUMO_CASEPATH> variable."
        ),
    )
    parser.add_argument(
        "--sumo",
        action="store_true",
        help="If passed, register the case on Sumo.",
    )

    # Deprecated

    parser.add_argument(
        "ert_config_path",
        type=Path,
        help="Deprecated and can safely be removed",
        nargs="?",  # Optional
        default=None,
    )
    parser.add_argument(
        "ert_casename",
        type=str,
        help="Deprecated and can safely be removed",
        nargs="?",  # Optional
        default=None,
    )
    parser.add_argument(
        "ert_username",
        type=str,
        help="Deprecated and can safely be removed",
        nargs="?",  # Optional
        default=None,
    )
    parser.add_argument(
        "--global_variables_path",
        type=Path,
        help="Path to global variables file relative to Ert config path.",
        default=None,
    )
    parser.add_argument(
        "--verbosity",
        type=str,
        help="Set log level",
        default=None,
    )
    parser.add_argument(
        "--sumo_env",
        type=str,
        help="Deprecated and can safely be removed",
        default=None,
    )
    return parser


class WfExportCaseMetadata(ert.ErtScript):
    """Legacy ERT workflow class for creating case metadata with a run() function
    that can be registered as an ERT plugin.

    This is used for the ERT workflow context. It is prefixed 'Wf' to avoid a
    potential naming collisions in fmu-dataio."""

    # Ensure ERT execution stops if the workflow fails
    stop_on_fail = True

    @staticmethod
    def validate(args: list[Any]) -> None:
        """Warn about deprecation when Ert validates the configured workflow."""
        ConfigWarning.deprecation_warn(DEPRECATION_MESSAGE)

    def run(
        self,
        workflow_args: list[str],
        ensemble: ErtEnsemble,
        run_paths: ErtRunpaths,
    ) -> None:
        """Parse arguments and run the workflow."""
        parser = get_parser()
        args = parser.parse_args(workflow_args)

        casepath = resolve_casepath(
            run_paths, args.casepath, require_sumo_casepath=args.sumo
        )
        maybe_fmu_dir = _copy_fmu_directory(casepath)

        cfg = CaseWorkflowConfig.from_presim_workflow(
            run_paths, args, casepath, maybe_fmu_dir
        )
        _run_workflow(ensemble, run_paths, cfg)


@ert.plugin(name="fmu_dataio")
def ertscript_workflow(config: ert.WorkflowConfigs) -> None:
    """Hook the WfExportCaseMetadata class with documentation into ERT."""
    config.add_workflow(
        WfExportCaseMetadata,
        "WF_CREATE_CASE_METADATA",
        parser=get_parser,
        description=DESCRIPTION,
        examples=EXAMPLES,
        category="export",
    )
