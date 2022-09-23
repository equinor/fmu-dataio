#!/usr/bin/env python

"""Create FMU case metadata and register case on Sumo (optional).

This script is intended to be run through an ERT HOOK PRESIM workflow.

Script will parse global variables from the template location. If
pointed towards the produced global_variables, fmu-config should run
before this script to make sure global_variables is updated."""

import yaml
import argparse
import logging
from pathlib import Path

try:
    from ert.shared.plugins.plugin_manager import hook_implementation  # type: ignore
except ModuleNotFoundError:
    from ert_shared.plugins.plugin_manager import hook_implementation  # type: ignore

try:
    from ert import ErtScript  # type: ignore
except ImportError:
    from res.job_queue import ErtScript  # type: ignore

from fmu.dataio import InitializeCase

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# This documentation is for ERT workflow
DESCRIPTION = """
WF_CREATE_CASE_METADATA will create case metadata with fmu-dataio and storing on disk
and on Sumo.
"""

EXAMPLES = """
Create an ERT workflow e.g. called ``ert/bin/workflows/create_case_metadata`` with the 
contents::
  WF_CREATE_CASE_METADATA <caseroot> <casename> <username> <sumo> <sumo_env>
  ...where
    <ert_caseroot> (Path): Absolute path to root of the case, typically <SCRATCH>/<US...
    <ert_config_path> (Path): Absolute path to ERT config, typically /project/etc/etc
    <ert_casename> (str): The ERT case name, typically <CASE_DIR>
    <ert_user> (str): The ERT user name, typically <USER>
    <sumo> (optional) (bool): If passed, do not register case on Sumo. Default: False
    <sumo_env> (str) (optional): Sumo environment to use. Default: "prod"
    <global_variables_path> (str): Path to global_variables relative to config path
    <verbosity> (str): Set log level. Default: WARNING

"""  # noqa


def main() -> None:
    """Entry point from command line"""

    # When script is called from an ERT workflow, it will be called through the 'run'
    # method on the WfCreateCaseMetadata class. This context is the intended usage.
    # The command line entry point is still included, to clarify the difference and
    # for debugging purposes.

    parser = get_parser()
    commandline_args = parser.parse_args()
    create_case_metadata_main(commandline_args)


class WfCreateCaseMetadata(ErtScript):
    """A class with a run() function that can be registered as an ERT plugin.

    This is used for the ERT workflow context."""

    # the class is prefixed Wf to avoid collision with a potential identical class
    # name in fmu-dataio

    # pylint: disable=too-few-public-methods
    def run(self, *args) -> None:
        # pylint: disable=no-self-use
        """Parse arguments and call _create_case_metadata_main()"""
        parser = get_parser()
        workflow_args = parser.parse_args(args)
        create_case_metadata_main(workflow_args)


def create_case_metadata_main(args) -> None:
    """Create the case metadata and register case on Sumo."""

    logger.setLevel(level=args.verbosity)
    check_arguments(args)
    case_metadata_path = create_metadata(args)
    register_on_sumo(args, case_metadata_path)

    logger.debug("create_case_metadata.py has finished.")


def create_metadata(args) -> str:
    """Create the case metadata and print them to the disk"""
    _global_variables_path = Path(args.ert_config_path, args.global_variables_path)
    global_variables = _parse_yaml(_global_variables_path)

    # fmu.dataio.InitializeCase class is scheduled to be renamed.

    case = InitializeCase(config=global_variables)
    case_metadata_path = case.export(
        rootfolder=args.ert_caseroot,
        casename=args.ert_casename,
        caseuser=args.ert_username,
        restart_from=None,
        description=None,
    )

    logger.info("Case metadata has been made: %s", case_metadata_path)

    return case_metadata_path


def register_on_sumo(args, case_metadata_path) -> str:
    """Register the case on Sumo by sending the case metadata"""

    env = args.sumo_env

    if args.sumo:
        logger.info("Registering case on Sumo (%s)", env)
    else:
        logger.info("Sumo registration has been deactivated through arguments")
        return

    # lazy loading of Sumo dependencies
    from fmu.sumo.uploader import SumoConnection, CaseOnDisk

    # establish connection
    sumo_conn = SumoConnection(env=env)
    logger.debug("Sumo connection established")

    # initiate the case on disk object.
    case = CaseOnDisk(case_metadata_path=case_metadata_path, sumo_connection=sumo_conn)

    # Register the case on Sumo
    sumo_id = case.register()

    logger.info("Case registered on Sumo with ID: %s", sumo_id)

    return sumo_id


def _parse_yaml(path):
    """Parse the global variables, return as dict"""

    with open(path, "r") as stream:
        data = yaml.safe_load(stream)

    return data


def check_arguments(args):
    """Do basic sanity checks of input"""

    logger.debug("Checking input arguments")
    logger.debug("arguments: %s", args)

    if not Path(args.ert_caseroot).is_absolute():
        logger.debug("Argument ert_caseroot was not absolute: %s", args.ert_caseroot)
        raise ValueError("ert_caseroot must be an absolute path")


def get_parser() -> argparse.ArgumentParser:
    """Construct parser object."""
    parser = argparse.ArgumentParser()
    parser.add_argument("ert_caseroot", type=str, help="Absolute path to the case root")
    parser.add_argument(
        "ert_config_path", type=str, help="ERT config path (<CONFIG_PATH>)"
    )
    parser.add_argument("ert_casename", type=str, help="ERT case name (<CASE>)")
    parser.add_argument("ert_username", type=str, help="ERT user name (<USER>)")
    parser.add_argument(
        "--sumo",
        action="store_true",
        help="If passed, register the case on Sumo.",
    )
    parser.add_argument("--sumo_env", type=str, help="Sumo environment", default="prod")
    parser.add_argument(
        "--global_variables_path",
        type=str,
        help="Directly specify path to global variables relative to ert config path",
        default="../../fmuconfig/output/global_variables.yml",
    )
    parser.add_argument(
        "--verbosity", type=str, help="Set log level", default="WARNING"
    )
    return parser


@hook_implementation
def legacy_ertscript_workflow(config) -> None:
    """Hook the WfCreateCaseMetadata class with documentation into ERT."""
    workflow = config.add_workflow(WfCreateCaseMetadata, "WF_CREATE_CASE_METADATA")
    workflow.parser = get_parser
    workflow.description = DESCRIPTION
    workflow.examples = EXAMPLES
    workflow.category = "export"


if __name__ == "__main__":
    main()
