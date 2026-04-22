"""Create FMU case metadata and register case on Sumo (optional).

This script is intended to be run through an Ert HOOK PRE_SIMULATION workflow.
"""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path
from typing import Final

import ert

from fmu.dataio._export import ExportConfig
from fmu.dataio._interfaces import SumoUploaderInterface
from fmu.dataio._metadata import generate_metadata
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import Content, FMUContext
from fmu.datamodels.standard_results.enums import (
    ErtObservations,
    StandardResultName,
)
from fmu.settings import (
    ProjectFMUDirectory,
    find_nearest_fmu_directory,
    get_fmu_directory,
)

from ._config import CaseWorkflowConfig
from ._observations import get_ert_observations_table
from ._parameters import get_ert_parameters_table
from .export_case_metadata import ExportCaseMetadata

logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# This documentation is compiled into ert's internal docs
DESCRIPTION = """
WF_CREATE_CASE_METADATA will create case metadata with fmu-dataio for storing on disk
and on Sumo.
"""

EXAMPLES = """
Create an Ert workflow e.g. called ``ert/bin/workflows/create_case_metadata`` with::

  WF_CREATE_CASE_METADATA <casepath> "--sumo"

Arguments:
    <casepath>: Absolute path to root of the case, typically <SCRATCH>/<USER>/<CASE_DIR>
    --sumo: Register case on Sumo
"""  # noqa: E501


def _get_ensemble_name(
    ensemble: ert.Ensemble,
    run_paths: ert.Runpaths,
    casepath: Path,
) -> str:
    """Determine ensemble name from run path.

    Users attribute the ensemble runpath directory as the ensemble name. This differs
    from the Ert internal view of the name. This function will collect the ensemble path
    from the first realization (since all realizations are placed within an ensemble).
    But if no ensemble directory is used the runpath would then be equal to the
    casepath. In this case use a default "iter-0".
    """
    runpath = Path(
        run_paths.get_paths(realizations=[0], iteration=ensemble.iteration)[0]
    )
    return str(runpath.name) if runpath.parent != casepath else "iter-0"


def _queue_ert_parameters(
    ensemble: ert.Ensemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export parameter table using fmu-dataio."""
    table = get_ert_parameters_table(ensemble)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.parameters)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=["REAL"])
        .file_config(name="parameters")
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .standard_result(StandardResultName.parameters)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_ert_observations_rft(
    ensemble: ert.Ensemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export rft observation table using fmu-dataio."""
    table = get_ert_observations_table(ensemble, "rft")
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
    ensemble: ert.Ensemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export summary observation table using fmu-dataio."""

    table = get_ert_observations_table(ensemble, "summary")
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


def _upload_files_to_sumo(
    ensemble: ert.Ensemble,
    run_paths: ert.Runpaths,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Establishes a case on Sumo, uploading initial case and ensemble data as well."""
    ensemble_name = _get_ensemble_name(ensemble, run_paths, workflow_config.casepath)
    _queue_ert_parameters(ensemble, ensemble_name, workflow_config, sumo_uploader)
    _queue_ert_observations_rft(ensemble, ensemble_name, workflow_config, sumo_uploader)
    _queue_ert_observations_summary(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    sumo_uploader.upload()


def _run_workflow(
    ensemble: ert.Ensemble,
    run_paths: ert.Runpaths,
    workflow_config: CaseWorkflowConfig,
) -> None:
    """Main workflow entry point."""
    logger.setLevel(workflow_config.verbosity)

    case_metadata_path = ExportCaseMetadata.from_workflow_config(
        workflow_config
    ).export()
    logger.debug(f"Case metadata exported to {case_metadata_path}")

    if workflow_config.register_on_sumo:
        sumo_uploader = SumoUploaderInterface.from_new_case(
            Path(case_metadata_path), workflow_config.global_config_path
        )
        _upload_files_to_sumo(ensemble, run_paths, workflow_config, sumo_uploader)


def _copy_fmu_directory(casepath: Path) -> ProjectFMUDirectory | None:
    """Copies the .fmu/ directory from the project path, if it exists, to the case path.

    If a .fmu/ directory already exists in the case path it will be overwritten.

    Returns:
        ProjectFMUDirectory instance on the case path or None.
    """
    try:
        fmu_dir = find_nearest_fmu_directory()
        shutil.copytree(fmu_dir.path, casepath / ".fmu", dirs_exist_ok=True)
    except FileNotFoundError:
        return None

    return get_fmu_directory(casepath)


def get_parser() -> argparse.ArgumentParser:
    """Construct parser object."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "casepath",
        type=Path,
        help="Absolute path to the case",
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
    """A class with a run() function that can be registered as an ERT plugin.

    This is used for the ERT workflow context. It is prefixed 'Wf' to avoid a
    potential naming collisions in fmu-dataio."""

    def run(
        self,
        workflow_args: list[str],
        ensemble: ert.Ensemble,
        run_paths: ert.Runpaths,
    ) -> None:
        """Parse arguments and run the workflow."""
        parser = get_parser()
        args = parser.parse_args(workflow_args)

        maybe_fmu_dir = _copy_fmu_directory(args.casepath)

        cfg = CaseWorkflowConfig.from_presim_workflow(run_paths, args, maybe_fmu_dir)
        _run_workflow(ensemble, run_paths, cfg)


@ert.plugin(name="fmu_dataio")
def ertscript_workflow(config: ert.CaseWorkflowConfigs) -> None:
    """Hook the WfExportCaseMetadata class with documentation into ERT."""
    config.add_workflow(
        WfExportCaseMetadata,
        "WF_CREATE_CASE_METADATA",
        parser=get_parser,
        description=DESCRIPTION,
        examples=EXAMPLES,
        category="export",
    )
