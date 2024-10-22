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

from ert.plugins.plugin_manager import hook_implementation

from fmu.dataio import ExportPreprocessedData

try:
    from ert.config import ErtScript
except ImportError:
    from res.job_queue import ErtScript

if TYPE_CHECKING:
    from ert.plugins.workflow_config import WorkflowConfigs

logger: Final = logging.getLogger(__name__)

# This documentation is compiled into ert's internal docs
DESCRIPTION = """
WF_COPY_PREPROCESSED_DATAIO will copy preprocessed data to a FMU run at
<caseroot>/share/observations/. If the data contains metadata this will be
updated with information about the FMU run and ready for upload to Sumo.

Preprocessed data refers to data that has been exported with dataio outside of a FMU
context, and is typically located in a share/preprocessed/ folder on the project disk.
"""

EXAMPLES = """
Create an ERT workflow e.g. named ``ert/bin/workflows/xhook_copy_preprocessed_data``
with the contents::
  WF_COPY_PREPROCESSED_DATAIO <SCRATCH>/<USER>/<CASE_DIR> <CONFIG_PATH> '../../share/preprocessed/'

Add following lines to your ERT config to have the job automatically executed::
  LOAD_WORKFLOW ../bin/workflows/xhook_copy_preprocessed_data
  HOOK_WORKFLOW xhook_copy_preprocessed_data PRE_SIMULATION
"""  # noqa


def main() -> None:
    """Entry point from command line

    When script is called from an ERT workflow, it will be called through the 'run'
    method on the WfCopyPreprocessedData class. This context is the intended usage.
    The command line entry point is still included, to clarify the difference and
    for debugging purposes.
    """
    parser = get_parser()
    commandline_args = parser.parse_args()
    copy_preprocessed_data_main(commandline_args)


class WfCopyPreprocessedData(ErtScript):
    """A class with a run() function that can be registered as an ERT plugin.

    This is used for the ERT workflow context. It is prefixed 'Wf' to avoid a
    potential naming collisions in fmu-dataio."""

    def run(self, *args: str) -> None:
        """Parse arguments and call copy_preprocessed_data_main()"""
        parser = get_parser()
        workflow_args = parser.parse_args(args)
        copy_preprocessed_data_main(workflow_args)


def copy_preprocessed_data_main(args: argparse.Namespace) -> None:
    """Copy the preprocessed data to scratch and upload it to sumo."""

    check_arguments(args)
    logger.setLevel(args.verbosity)

    searchpath = Path(args.ert_config_path) / args.inpath
    match_pattern = "[!.]*"  # ignore metafiles (starts with '.')
    files = [f for f in searchpath.rglob(match_pattern) if f.is_file()]
    logger.debug("files found %s", files)

    if not files:
        raise ValueError(f"No files found in {searchpath=}, check spelling.")

    logger.info("Starting to copy preprocessed files to <caseroot>/share/observations/")
    for filepath in files:
        ExportPreprocessedData(
            casepath=args.ert_caseroot,
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

    if not Path(args.ert_caseroot).is_absolute():
        logger.debug("Argument 'ert_caseroot' was not absolute: %s", args.ert_caseroot)
        raise ValueError("'ert_caseroot' must be an absolute path")

    if Path(args.inpath).is_absolute():
        logger.debug("Argument 'inpath' is absolute: %s", args.inpath)
        raise ValueError(
            "'inpath' is an absolute path, it should be relative to the ert_configpath",
        )


def get_parser() -> argparse.ArgumentParser:
    """Construct parser object."""
    parser = argparse.ArgumentParser()
    parser.add_argument("ert_caseroot", type=str, help="Absolute path to the case root")
    parser.add_argument(
        "ert_config_path", type=str, help="ERT config path (<CONFIG_PATH>)"
    )
    parser.add_argument(
        "inpath",
        type=str,
        help="Folder with preprocessed data relative to ert_configpath.",
        default="../../share/preprocessed",
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


@hook_implementation
def legacy_ertscript_workflow(config: WorkflowConfigs) -> None:
    """Hook the WfCopyPreprocessedData class with documentation into ERT."""
    workflow = config.add_workflow(
        WfCopyPreprocessedData, "WF_COPY_PREPROCESSED_DATAIO"
    )
    workflow.parser = get_parser
    workflow.description = DESCRIPTION
    workflow.examples = EXAMPLES
    workflow.category = "export"


if __name__ == "__main__":
    main()
