"""Create FMU case metadata and register case on Sumo (optional).

This script is intended to be run through an Ert HOOK PRE_SIMULATION workflow.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

import ert

from fmu.dataio._interfaces import SumoUploaderInterface
from fmu.dataio._workflows.fmu_pre_sim.export_case_metadata import (
    ExportCaseMetadata,
)
from fmu.dataio._workflows.fmu_pre_sim.main import (
    _copy_fmu_directory,
    _upload_files_to_sumo,
)

from .._utils import resolve_casepath
from ._config import CaseWorkflowConfig

if TYPE_CHECKING:
    from ert.runpaths import Runpaths as ErtRunpaths
    from ert.storage import Ensemble as ErtEnsemble


logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# This documentation is compiled into ert's internal docs
DESCRIPTION = """
WF_CREATE_CASE_METADATA will create case metadata with fmu-dataio for storing on disk
and on Sumo. When Sumo upload is enabled, the workflow also uploads Ert parameters
and observations, including summary, RFT, breakthrough, and seismic observations. The
workflow uses Ert storage directly, so the relevant case metadata, parameters, and
observations are collected automatically from the active Ert run.
"""

EXAMPLES = """
Create an Ert workflow e.g. called ``ert/bin/workflows/xhook_create_case_metadata`` with::

    WF_CREATE_CASE_METADATA "--sumo"

Arguments:
    --sumo: Register case on Sumo

Note that ``<SUMO_CASEPATH>`` must be defined in the Ert config for this workflow to run::

    DEFINE <SUMO_CASEPATH>  <SCRATCH>/<USER>/<CASE_DIR>

"""  # noqa: E501


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
