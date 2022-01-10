#!/usr/bin/env python

"""

Initialize an FMU case with metadata and Sumo registration (optional).
This script is intended to be run through an ERT HOOK PRESIM workflow.

Script will parse global variables from the template location. If
pointed towards the produced global_variables, fmu-config should run
before this script to make sure global_variables is updated.

"""
import yaml
import argparse
import logging
from pathlib import Path

from ert_shared.plugins.plugin_manager import hook_implementation  # type: ignore
from res.job_queue import ErtScript  # type: ignore

from fmu.config._loader import FmuLoader
from fmu.dataio import InitializeCase
from fmu.sumo.uploader import SumoConnection, CaseOnDisk

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# This documentation is for ERT workflow
DESCRIPTION = """
WF_INITIALIZE_CASE will initialize a case with fmu-dataio by producing case metadata
and registering the case on Sumo (optional)
"""

EXAMPLES = """
Create an ERT workflow e.g. called ``ert/bin/workflows/initialize_case`` with the 
contents::
  WF_INITIALIZE_CASE <caseroot> <casename> <username> <sumo> <sumo_env>
  ...where
    <ert_caseroot> (Path): Absolute path to root of the case, typically <SCRATCH>/<US...
    <ert_config_path> (Path): Absolute path to ERT config, typically /project/etc/etc
    <ert_casename> (str): The ERT case name, typically <CASE_DIR>
    <ert_user> (str): The ERT user name, typically <USER>
    <sumo> (optional) (bool): If passed, do not register case on Sumo. Default: False
    <sumo_env> (str) (optional): Sumo environment to use. Default: "prod"
    <global_variables_path> (str): Path to global_variables relative to config path
    <verbose> (str): Set log level to INFO. Default: WARNING

"""  # noqa


def main() -> None:
    """Entry point from command line"""

    # this is technically never to be used, but assuming it will be more confusing
    # to remove it than to leave it in. Since it is here, making sure that it will
    # work if called. When script is called from an ERT workflow, it will be called
    # through the 'run' method on the WfInitializeCase class.

    parser = get_parser()
    commandline_args = parser.parse_args()
    initialize_case_main(commandline_args)


class WfInitializeCase(ErtScript):
    """A class with a run() function that can be registered as an ERT plugin.

    This is used for the ERT workflow context."""

    # the class is prefixed Wf to avoid collision with fmu.dataio.InitializeCase

    # pylint: disable=too-few-public-methods
    def run(self, *args) -> None:
        # pylint: disable=no-self-use
        """Parse arguments and call _initialize_case_main()"""
        parser = get_parser()
        workflow_args = parser.parse_args(args)
        initialize_case_main(workflow_args)


def initialize_case_main(args) -> None:
    """Initialize the case and register on Sumo if applicable."""

    if args.verbose:
        logger.setLevel(level=logging.INFO)
    if args.debug:
        logger.setLevel(level=logging.DEBUG)

    check_arguments(args)
    case_metadata_path = create_metadata(args)
    register_on_sumo(args, case_metadata_path)

    logger.debug("initialize_case.py has finished.")


def create_metadata(args) -> str:
    """Create the case metadata and print them to the disk"""
    _global_variables_path = Path(args.ert_config_path, args.global_variables_path)
    global_variables = _parse_yaml(_global_variables_path)

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
        data = yaml.load(stream, Loader=FmuLoader)

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
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information",
    )
    return parser


@hook_implementation
def legacy_ertscript_workflow(config) -> None:
    """Hook the InitializeCase class into ERT with the name WF_INITIALIZE_CASE,
    and inject documentation"""
    workflow = config.add_workflow(WfInitializeCase, "WF_INITIALIZE_CASE")
    workflow.parser = get_parser
    workflow.description = DESCRIPTION
    workflow.examples = EXAMPLES
    workflow.category = "export"


if __name__ == "__main__":
    main()
