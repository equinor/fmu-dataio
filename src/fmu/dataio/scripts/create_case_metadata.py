"""Create FMU case metadata and register case on Sumo (optional).

This script is intended to be run through an ERT HOOK PRESIM workflow.

Script will parse global variables from the template location. If
pointed towards the produced global_variables, fmu-config should run
before this script to make sure global_variables is updated."""

from __future__ import annotations

import argparse
import logging
import os
import warnings
from pathlib import Path
from typing import Any, Final

import ert
import yaml
from pydantic import TypeAdapter

from fmu.dataio import CreateCaseMetadata, ExportData
from fmu.datamodels import ErtParameterMetadata
from fmu.datamodels.fmu_results.standard_result import ErtParametersStandardResult
from fmu.datamodels.standard_results.enums import StandardResultName

logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# This documentation is compiled into ert's internal docs
DESCRIPTION = """
WF_CREATE_CASE_METADATA will create case metadata with fmu-dataio for storing on disk
and on Sumo.
"""

EXAMPLES = """
Create an ERT workflow e.g. called ``ert/bin/workflows/create_case_metadata`` with the
contents::
  WF_CREATE_CASE_METADATA <ert_caseroot> <ert_config_path> <ert_casename> "--sumo"
  ...where
    <ert_caseroot> (Path): Absolute path to root of the case, typically <SCRATCH>/<US...
    <ert_config_path> (Path): Absolute path to ERT config, typically /project/etc/etc
    <ert_casename> (str): The ERT case name, typically <CASE_DIR>
    <sumo> (optional) (bool): If passed, do not register case on Sumo. Default: False
    <global_variables_path> (str): Path to global_variables relative to config path
    <verbosity> (str): Set log level. Default: WARNING
"""

ErtParameterMetadataAdapter: TypeAdapter[ErtParameterMetadata] = TypeAdapter(
    ErtParameterMetadata
)


class WfCreateCaseMetadata(ert.ErtScript):
    """A class with a run() function that can be registered as an ERT plugin.

    This is used for the ERT workflow context. It is prefixed 'Wf' to avoid a
    potential naming collisions in fmu-dataio."""

    # pylint: disable=too-few-public-methods
    def run(self, workflow_args: list[str], ensemble: ert.Ensemble) -> None:
        # pylint: disable=no-self-use
        """Parse arguments and call main()"""
        parser = get_parser()
        args = parser.parse_args(workflow_args)
        main(args, ensemble)


@ert.plugin(name="fmu_dataio")
def ertscript_workflow(config: ert.WorkflowConfigs) -> None:
    """Hook the WfCreateCaseMetadata class with documentation into ERT."""
    config.add_workflow(
        WfCreateCaseMetadata,
        "WF_CREATE_CASE_METADATA",
        parser=get_parser,
        description=DESCRIPTION,
        examples=EXAMPLES,
        category="export",
    )


def _load_global_config(global_config_path: Path) -> dict[str, Any]:
    """Load this simulation's global config."""
    logger.debug(f"Loading global config from {global_config_path}")
    with open(global_config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(args: argparse.Namespace, ensemble: ert.Ensemble) -> None:
    """Create the case metadata and register case on Sumo."""
    check_arguments(args)
    logger.setLevel(args.verbosity)

    global_config_path = args.ert_config_path / args.global_variables_path
    global_config = _load_global_config(global_config_path)

    case_metadata_path = create_case_metadata(
        global_config, args.ert_caseroot, args.ert_casename, args.sumo
    )
    logger.debug(f"Case metadata exported to {case_metadata_path}")

    export_ert_parameters(ensemble, args.ert_caseroot, global_config)
    logger.debug("create_case_metadata.py has finished.")


def _genkw_config_to_parameter_metadata(
    config: ert.config.GenKwConfig,
) -> ErtParameterMetadata:
    distribution_dict = config.distribution.model_dump(exclude={"name"})
    return ErtParameterMetadataAdapter.validate_python(
        {
            "group": config.group,
            "input_source": config.input_source,
            "distribution": config.distribution.name.lower(),
            **distribution_dict,
        }
    )


def export_ert_parameters(
    ensemble: ert.Ensemble, casepath: Path, global_config: dict[str, Any]
) -> Path:
    """Exports Ert parameters as a Parquet file as the ensemble level."""
    import pyarrow as pa

    scalars_df = ensemble.load_scalars()

    if scalars_df.is_empty():
        logger.warning("No scalar parameters found in ensemble")
        return casepath

    realizations = scalars_df.get_column("realization").to_list()
    logger.debug(
        f"Found {len(scalars_df)} parameters for {len(realizations)} realizations"
    )

    param_configs = ensemble.experiment.parameter_configuration

    fields: list[pa.Field] = [pa.field("realization", pa.int64())]
    column_renames: dict[str, str] = {}
    columns_to_drop: list[str] = []

    for col_name in scalars_df.columns:
        if col_name == "realization":
            continue

        _, param_name = (
            col_name.split(":", 1) if ":" in col_name else ("DEFAULT", col_name)
        )

        config = param_configs.get(param_name)
        if config is not None and isinstance(config, ert.config.GenKwConfig):
            metadata = _genkw_config_to_parameter_metadata(config)
            fields.append(
                pa.field(param_name, pa.float64(), metadata=metadata.to_pa_metadata())
            )
            column_renames[col_name] = param_name
        else:
            columns_to_drop.append(col_name)
            logger.warning(
                f"Skipping parameter '{col_name}': no valid GenKwConfig found"
            )

    scalars_df = scalars_df.drop(columns_to_drop).rename(column_renames)

    schema = pa.schema(fields)
    table = scalars_df.to_arrow().cast(schema)

    ed = ExportData(
        config=global_config,
        casepath=casepath,
        content="parameters",
        name="parameters",
        table_index=["realization"],
        fmu_context="ensemble",
    )

    export_config = ed._export_config.with_ensemble_name(ensemble.name)

    export_path = ed._export_with_standard_result(
        table,
        ErtParametersStandardResult(name=StandardResultName.parameters),
        export_config,
    )

    logger.info(f"Exported parameters for realizations {realizations} to {export_path}")

    return Path(export_path)


def create_case_metadata(
    global_config: dict[str, Any], ert_caseroot: Path, ert_casename: str, sumo: bool
) -> str:
    """Create the case metadata and print them to the disk"""
    case_metadata_path = CreateCaseMetadata(
        config=global_config,
        rootfolder=ert_caseroot,
        casename=ert_casename,
    ).export()

    if sumo:
        sumo_env = os.environ.get("SUMO_ENV", "prod")
        logger.info(f"Registering case on Sumo ({sumo_env})")
        register_on_sumo(sumo_env, case_metadata_path)

    return case_metadata_path


def register_on_sumo(
    sumo_env: str,
    case_metadata_path: str,
) -> str:
    """Register the case on Sumo by sending the case metadata"""
    from fmu.sumo.uploader import CaseOnDisk, SumoConnection

    sumo_conn = SumoConnection(sumo_env)
    logger.debug("Sumo connection established")
    case = CaseOnDisk(case_metadata_path, sumo_conn)
    sumo_id = case.register()

    logger.info("Case registered on Sumo with ID: %s", sumo_id)
    return sumo_id


def check_arguments(args: argparse.Namespace) -> None:
    """Do basic sanity checks of input"""
    logger.debug("Checking input arguments")
    logger.debug("Arguments: %s", args)

    casepath = args.ert_caseroot
    casepath_str = str(casepath)

    if not casepath.is_absolute():
        logger.debug("Argument ert_caseroot was not absolute: %s", casepath)
        if casepath_str.startswith("<") and casepath_str.endswith(">"):
            raise ValueError(
                f"ERT variable used for the case root is not defined: {casepath}"
            )
        raise ValueError(
            "The 'ert_caseroot' argument must be an absolute path, "
            f"received {casepath}."
        )

    if args.ert_username:
        warnings.warn(
            "The argument 'ert_username' is deprecated. It is no "
            "longer used and can safely be removed.",
            FutureWarning,
        )
    if args.sumo_env:
        if args.sumo_env == "prod":
            warnings.warn(
                "The argument 'sumo_env' is ignored and can safely be removed.",
                FutureWarning,
            )
        else:
            if os.getenv("SUMO_ENV") is None:
                raise ValueError(
                    "Setting sumo environment through argument input is not allowed. "
                    "It must be set as an environment variable SUMO_ENV"
                )


def get_parser() -> argparse.ArgumentParser:
    """Construct parser object."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ert_caseroot", type=Path, help="Absolute path to the case root"
    )
    parser.add_argument(
        "ert_config_path", type=Path, help="ERT config path (<CONFIG_PATH>)"
    )
    parser.add_argument("ert_casename", type=str, help="ERT case name (<CASE>)")
    parser.add_argument(
        "ert_username",
        type=str,
        help="Deprecated and can safely be removed",
        nargs="?",  # Makes it optional
        default=None,
    )
    parser.add_argument(
        "--sumo",
        action="store_true",
        help="If passed, register the case on Sumo.",
    )
    parser.add_argument(
        "--sumo_env",
        type=str,
        help="Deprecated and can safely be removed",
        default=None,
    )
    parser.add_argument(
        "--global_variables_path",
        type=Path,
        help="Directly specify path to global variables relative to ert config path",
        default="../../fmuconfig/output/global_variables.yml",
    )
    parser.add_argument(
        "--verbosity", type=str, help="Set log level", default="WARNING"
    )
    return parser


def _main() -> None:
    """Entry point from command line

    When script is called from an ERT workflow, it will be called through the 'run'
    method on the WfCreateCaseMetadata class. This context is the intended usage.
    The command line entry point is still included, to clarify the difference and
    for debugging purposes.
    """
    parser = get_parser()
    args = parser.parse_args()
    global_config_path = args.ert_config_path / args.global_variables_path
    global_config = _load_global_config(global_config_path)
    create_case_metadata(global_config, args.ert_caseroot, args.ert_casename, args.sumo)


if __name__ == "__main__":
    _main()
