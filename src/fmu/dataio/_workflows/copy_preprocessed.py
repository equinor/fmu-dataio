#!/usr/bin/env python

"""Copy preprocessed data to an FMU case while updating the metadata.

This script is intended to be run through an ERT HOOK PRESIM workflow.

"""

from __future__ import annotations

import argparse
import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Final

import ert

from fmu.dataio import ExportPreprocessedData

from ._utils import resolve_casepath

if TYPE_CHECKING:
    from ert.runpaths import Runpaths as ErtRunpaths

logger: Final = logging.getLogger(__name__)

# This documentation is compiled into ert's internal docs
DESCRIPTION = """
WF_COPY_PREPROCESSED_DATAIO will copy preprocessed data to a FMU run at
<SUMO_CASEPATH>/share/observations/. If the data contains metadata this will be
updated with information about the FMU run and ready for upload to Sumo.

Preprocessed data refers to data that has been exported with dataio outside of a FMU
context, and is typically located in a share/preprocessed/ folder on the project disk.
"""

EXAMPLES = """
Create an ERT workflow e.g. named ``ert/bin/workflows/xhook_copy_preprocessed_data``
with the contents::

    WF_COPY_PREPROCESSED_DATAIO '../../share/preprocessed/'

The case path is read from ``<SUMO_CASEPATH>`` and the input path is resolved
relative to ``<CONFIG_PATH>``.

Add following lines to your ERT config to have the job automatically executed::

  LOAD_WORKFLOW ../bin/workflows/xhook_copy_preprocessed_data
  HOOK_WORKFLOW xhook_copy_preprocessed_data PRE_SIMULATION

"""  # noqa


class WfCopyPreprocessedData(ert.ErtScript):
    """A class with a run() function that can be registered as an ERT plugin.

    This is used for the ERT workflow context. It is prefixed 'Wf' to avoid a
    potential naming collisions in fmu-dataio."""

    def run(
        self,
        workflow_args: list[str],
        run_paths: ErtRunpaths,
    ) -> None:
        """Parse arguments and call copy_preprocessed_data_main()."""
        parser = get_parser()
        args = parser.parse_args(workflow_args)
        copy_preprocessed_data_main(args, run_paths)


def copy_preprocessed_data_main(
    args: argparse.Namespace, run_paths: ErtRunpaths
) -> None:
    """Copy the preprocessed data to scratch and upload it to sumo."""

    _normalize_workflow_arguments(args)
    check_arguments(args)
    logger.setLevel(args.verbosity)

    casepath = resolve_casepath(run_paths, args.ert_caseroot)
    ert_config_path = Path(run_paths.substitutions["<CONFIG_PATH>"])
    searchpath = ert_config_path / args.inpath

    match_pattern = "[!.]*"  # ignore metafiles (starts with '.')
    files = [
        filepath
        for filepath in searchpath.rglob(match_pattern)
        if filepath.is_file() and not filepath.is_symlink()
    ]
    logger.debug("files found %s", files)

    if not files:
        raise ValueError(f"No files found in {searchpath=}, check spelling.")

    logger.info("Starting to copy preprocessed files to <caseroot>/share/observations/")
    for filepath in files:
        ExportPreprocessedData(
            casepath=casepath,
            is_observation=True,
        ).export(filepath)
        logger.info("Copied preprocessed file %s", filepath)

    logger.debug("copy_preprocessed_data_main.py has finished.")


def check_arguments(args: argparse.Namespace) -> None:
    """Do basic sanity checks of input"""
    logger.debug("Checking input arguments")
    logger.debug("Arguments: %s", args)

    if args.global_variables_path:
        warnings.warn(
            "The global variables path is no longer needed. Please remove the "
            "'--global_variables_path' argument and path from the workflow file.",
            FutureWarning,
        )

    if args.ert_config_path:
        warnings.warn(
            "The argument 'ert_config_path' is deprecated. It is no longer used "
            "and can safely be removed from WF_COPY_PREPROCESSED_DATAIO.",
            FutureWarning,
        )

    if Path(args.inpath).is_absolute():
        logger.debug("Argument 'inpath' is absolute: %s", args.inpath)
        raise ValueError(
            "'inpath' is an absolute path, it should be relative to the ert_configpath",
        )


def _normalize_workflow_arguments(args: argparse.Namespace) -> None:
    """Normalize the current and deprecated positional argument layouts."""
    if len(args.paths) == 1:
        args.ert_caseroot = None
        args.ert_config_path = None
        args.inpath = args.paths[0]
        return

    if len(args.paths) == 3:
        args.ert_caseroot, args.ert_config_path, args.inpath = args.paths
        return

    raise ValueError(
        "WF_COPY_PREPROCESSED_DATAIO expects either <inpath> or the deprecated "
        "<ert_caseroot> <ert_config_path> <inpath> arguments."
    )


def get_parser() -> argparse.ArgumentParser:
    """Construct parser object."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths",
        nargs="+",
        type=str,
        metavar="PATH",
        help=(
            "Input folder relative to <CONFIG_PATH>. The deprecated three-value "
            "form is also accepted."
        ),
    )
    parser.add_argument(
        "--global_variables_path",
        type=str,
        help="Deprecated and should be not be used",
    )
    parser.add_argument(
        "--verbosity", type=str, help="Set log level", default="WARNING"
    )
    return parser


@ert.plugin(name="fmu_dataio")
def ertscript_workflow(config: ert.WorkflowConfigs) -> None:
    """Hook the WfCopyPreprocessedData class with documentation into ERT."""
    config.add_workflow(
        WfCopyPreprocessedData,
        "WF_COPY_PREPROCESSED_DATAIO",
        parser=get_parser,
        description=DESCRIPTION,
        examples=EXAMPLES,
        category="export",
    )
