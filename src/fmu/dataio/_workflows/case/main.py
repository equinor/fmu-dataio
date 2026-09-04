"""Create FMU case metadata and register case on Sumo (optional).

This script is intended to be run through an Ert HOOK PRE_SIMULATION workflow.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Final

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
from ._mappings import get_stratigraphy_mappings_table, get_wellbore_mappings_table
from ._observations import get_ert_observations_table
from ._parameters import get_ert_parameters_table
from .export_case_metadata import ExportCaseMetadata

if TYPE_CHECKING:
    from ert.runpaths import Runpaths as ErtRunpaths
    from ert.storage import Ensemble as ErtEnsemble


logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# This documentation is compiled into ert's internal docs
DESCRIPTION = """
WF_CREATE_CASE_METADATA will create case metadata with fmu-dataio for storing on disk
and on Sumo. When Sumo upload is enabled, the workflow also uploads Ert parameters
and observations, including summary, RFT, and breakthrough observations. The workflow
uses Ert storage directly, so the relevant case metadata, parameters, and observations
are collected automatically from the active Ert run.
"""

EXAMPLES = """
Create an Ert workflow e.g. called ``ert/bin/workflows/xhook_create_case_metadata`` with::

    WF_CREATE_CASE_METADATA "--sumo"

Arguments:
    --sumo: Register case on Sumo

Note that ``<SUMO_CASEPATH>`` must be defined in the Ert config for this workflow to run::

    DEFINE <SUMO_CASEPATH>  <SCRATCH>/<USER>/<CASE_DIR>

"""  # noqa: E501


def _validate_casepath(casepath: Path) -> Path:
    """Validate that the case path is absolute and defined in the ERT config."""
    if not casepath.is_absolute():
        casepath_str = str(casepath)
        if casepath_str.startswith("<") and casepath_str.endswith(">"):
            raise ValueError(f"Ert variable for casepath is not defined: {casepath}")
        raise ValueError(f"'casepath' must be an absolute path. Got: {casepath}")
    return casepath


def _resolve_casepath(run_paths: ErtRunpaths, args: argparse.Namespace) -> Path:
    """Resolve and validate case path from <SUMO_CASEPATH> or deprecated argument.

    Uses <SUMO_CASEPATH> when defined and warns if deprecated <casepath> argument
    is also provided. If Sumo is enabled but <SUMO_CASEPATH> is missing, an error
    is raised, otherwise it falls back to <casepath> argument if provided.
    """

    sumo_casepath = run_paths.substitutions.get("<SUMO_CASEPATH>")

    if sumo_casepath:
        if args.casepath:
            warnings.warn(
                "The argument 'casepath' is deprecated. It is no longer used and can "
                "safely be removed from WF_CREATE_CASE_METADATA. The case path is now "
                "read from the <SUMO_CASEPATH> variable.",
                FutureWarning,
            )
        return _validate_casepath(Path(sumo_casepath))

    if args.casepath:
        if args.sumo:
            raise ValueError(
                "Missing required <SUMO_CASEPATH> definition. "
                "Define it in your ERT config, for example:\n"
                "DEFINE <SUMO_CASEPATH> <SCRATCH>/<USER>/<CASE_DIR>"
            )
        return _validate_casepath(Path(args.casepath))

    raise ValueError(
        "The case path could not be resolved. Please define the <SUMO_CASEPATH> "
        "variable in the ERT config, for example:\n\n    "
        "DEFINE <SUMO_CASEPATH> <SCRATCH>/<USER>/<CASE_DIR>"
    )


def _get_ensemble_name(
    ensemble: ErtEnsemble,
    run_paths: ErtRunpaths,
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
    ensemble: ErtEnsemble,
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


def _queue_ert_observations_breakthrough(
    ensemble: ErtEnsemble,
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export breakthrough observation table using fmu-dataio."""

    table = get_ert_observations_table(ensemble, "breakthrough")
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
    ensemble: ErtEnsemble,
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


def _queue_stratigraphy_mappings(
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export stratigraphy mappings using fmu-dataio."""
    assert workflow_config.fmu_dir is not None

    table = get_stratigraphy_mappings_table(workflow_config.fmu_dir)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.mapping)
        .access(Classification.internal, rep_include=False)
        .file_config(name=StandardResultName.stratigraphy_mapping.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .flags(is_observation=True)
        .standard_result(StandardResultName.stratigraphy_mapping)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_wellbore_mappings(
    ensemble_name: str,
    workflow_config: CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export wellbore mappings using fmu-dataio."""
    assert workflow_config.fmu_dir is not None

    table = get_wellbore_mappings_table(workflow_config.fmu_dir)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.mapping)
        .access(Classification.internal, rep_include=False)
        .file_config(name=StandardResultName.wellbore_mapping.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .flags(is_observation=True)
        .standard_result(StandardResultName.wellbore_mapping)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _upload_files_to_sumo(
    ensemble: ErtEnsemble,
    run_paths: ErtRunpaths,
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
    _queue_ert_observations_breakthrough(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )

    if workflow_config.fmu_dir:
        _queue_stratigraphy_mappings(ensemble_name, workflow_config, sumo_uploader)
        _queue_wellbore_mappings(ensemble_name, workflow_config, sumo_uploader)

    sumo_uploader.upload()


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
    """A class with a run() function that can be registered as an ERT plugin.

    This is used for the ERT workflow context. It is prefixed 'Wf' to avoid a
    potential naming collisions in fmu-dataio."""

    # Ensure ERT execution stops if the workflow fails
    stop_on_fail = True

    def run(
        self,
        workflow_args: list[str],
        ensemble: ErtEnsemble,
        run_paths: ErtRunpaths,
    ) -> None:
        """Parse arguments and run the workflow."""
        parser = get_parser()
        args = parser.parse_args(workflow_args)

        casepath = _resolve_casepath(run_paths, args)
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
