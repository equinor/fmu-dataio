"""Create FMU case metadata and register case on Sumo (optional).

This script is intended to be run through an Ert HOOK PRE_SIMULATION workflow.
"""

from __future__ import annotations

import argparse
import logging
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import ert
import yaml
from pydantic import TypeAdapter, ValidationError

from fmu.dataio import CreateCaseMetadata
from fmu.dataio._export import export_with_metadata
from fmu.dataio._export_config import ExportConfig
from fmu.datamodels import ErtParameterMetadata
from fmu.datamodels.fmu_results import global_configuration
from fmu.datamodels.fmu_results.enums import Content, FMUContext
from fmu.datamodels.standard_results.enums import StandardResultName

if TYPE_CHECKING:
    import polars as pl
    import pyarrow as pa

logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# This documentation is compiled into ert's internal docs
DESCRIPTION = """
WF_CREATE_CASE_METADATA will create case metadata with fmu-dataio for storing on disk
and on Sumo.
"""

EXAMPLES = """
Create an Ert workflow e.g. called ``ert/bin/workflows/create_case_metadata`` with::

  WF_CREATE_CASE_METADATA <casepath> <ert_config_path> "--sumo"

Arguments:
    <casepath>: Absolute path to root of the case, typically <SCRATCH>/<USER>/<CASE_DIR>
    <ert_config_path>: Absolute path to the Ert config, typically <CONFIG_PATH>
    --sumo: Register case on Sumo
"""  # noqa: E501

ErtParameterMetadataAdapter: TypeAdapter[ErtParameterMetadata] = TypeAdapter(
    ErtParameterMetadata
)


@dataclass(frozen=True)
class WorkflowConfig:
    """Validated workflow configuration."""

    casepath: Path
    ert_config_path: Path
    global_variables_path: Path
    register_on_sumo: bool
    verbosity: str

    @property
    def casename(self) -> str:
        return self.casepath.name

    @property
    def global_config_path(self) -> Path:
        return self.ert_config_path / self.global_variables_path

    def validate(self) -> None:
        casepath_str = str(self.casepath)
        if not self.casepath.is_absolute():
            if casepath_str.startswith("<") and casepath_str.endswith(">"):
                raise ValueError(
                    f"Ert variable for case root is not defined: {self.casepath}"
                )
            raise ValueError(
                f"'casepath' must be an absolute path. Got: {self.casepath}"
            )


def _load_global_config(global_config_path: Path) -> dict[str, Any]:
    """Load this simulation's global config."""
    logger.debug(f"Loading global config from {global_config_path}")
    with open(global_config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_case_metadata(
    workflow_config: WorkflowConfig, global_config: dict[str, Any]
) -> str:
    """Create the case metadata and print them to the disk"""
    case_metadata_path = CreateCaseMetadata(
        config=global_config,
        rootfolder=workflow_config.casepath,
        casename=workflow_config.casename,
    ).export()

    if workflow_config.register_on_sumo:
        _register_on_sumo(case_metadata_path)

    return case_metadata_path


def _register_on_sumo(case_metadata_path: str) -> str:
    """Register the case on Sumo by sending the case metadata"""
    from fmu.sumo.uploader import CaseOnDisk, SumoConnection

    sumo_env = os.environ.get("SUMO_ENV", "prod")
    logger.info(f"Registering case on Sumo ({sumo_env})")

    sumo_conn = SumoConnection(sumo_env)
    logger.debug("Sumo connection established")
    case = CaseOnDisk(case_metadata_path, sumo_conn)
    sumo_id = case.register()

    logger.info("Case registered on Sumo with ID: %s", sumo_id)
    return sumo_id


def export_ert_parameters(
    ensemble: ert.Ensemble,
    run_paths: ert.Runpaths,
    casepath: Path,
    global_config: global_configuration.GlobalConfiguration,
) -> Path:
    """Exports Ert parameters as a Parquet file as the ensemble level."""

    scalars_df = ensemble.load_scalars()
    if scalars_df.is_empty():
        logger.warning("No scalar parameters found in ensemble")
        return casepath

    ensemble_name = _get_ensemble_name(ensemble, run_paths, casepath)
    table, realizations = _process_parameters(scalars_df, ensemble)

    export_path = _export_parameters_table(
        table, ensemble_name, casepath, global_config
    )
    logger.info(f"Exported parameters for realizations {realizations} to {export_path}")
    return export_path


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


def _process_parameters(
    scalars_df: pl.DataFrame, ensemble: ert.Ensemble
) -> tuple[pa.Table, list[int]]:
    """Process parameters into an Arrow table with metadata."""
    import pyarrow as pa

    param_configs = ensemble.experiment.parameter_configuration
    realizations = scalars_df.get_column("realization").to_list()

    columns_to_drop: list[str] = []
    metadata_map: dict[str, dict[bytes, bytes]] = {}
    rename_map: dict[str, str] = {
        "realization": "REAL",
    }

    for col_name in scalars_df.columns:
        if col_name == "realization":
            continue

        param_name: str = col_name.split(":", 1)[-1] if ":" in col_name else col_name
        config = param_configs.get(param_name)

        if isinstance(config, ert.config.GenKwConfig):
            metadata = _genkw_to_metadata(config)
            metadata_map[param_name] = metadata.to_pa_metadata()
            rename_map[col_name] = param_name
        else:
            columns_to_drop.append(col_name)
            logger.warning(f"Skipping '{col_name}': no valid GenKwConfig found")

    scalars_df = scalars_df.drop(columns_to_drop).rename(rename_map)
    arrow_table = scalars_df.to_arrow()

    fields = [
        pa.field(f.name, f.type, metadata=metadata_map.get(f.name))
        for f in arrow_table.schema
    ]
    table = arrow_table.cast(pa.schema(fields))

    return table, realizations


def _genkw_to_metadata(config: ert.config.GenKwConfig) -> ErtParameterMetadata:
    """Convert GenKwConfig to parameter metadata."""
    distribution_dict = config.distribution.model_dump(exclude={"name"})
    return ErtParameterMetadataAdapter.validate_python(
        {
            "group": config.group or "DEFAULT",
            "input_source": config.input_source,
            "distribution": config.distribution.name.lower(),
            **distribution_dict,
        }
    )


def _export_parameters_table(
    table: pa.Table,
    ensemble_name: str,
    casepath: Path,
    global_config: global_configuration.GlobalConfiguration,
) -> Path:
    """Export parameter table using fmu-dataio."""
    export_config = (
        ExportConfig.builder()
        .content(Content.parameters)
        .table_config(table_index=["REAL"])
        .file_config(name="parameters")
        .global_config(global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=casepath,
        )
        .standard_result(StandardResultName.parameters)
        .build()
    )
    return export_with_metadata(export_config, table)


def get_parser() -> argparse.ArgumentParser:
    """Construct parser object."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "casepath",
        type=Path,
        help="Absolute path to the case",
    )
    parser.add_argument(
        "ert_config_path",
        type=Path,
        help="Ert config path (<CONFIG_PATH>)",
    )
    parser.add_argument(
        "--sumo",
        action="store_true",
        help="If passed, register the case on Sumo.",
    )
    parser.add_argument(
        "--global_variables_path",
        type=Path,
        help="Path to global variables file relative to Ert config path.",
        default="../../fmuconfig/output/global_variables.yml",
    )

    # Deprecated/unneeded below

    parser.add_argument(
        "ert_casename",
        type=str,
        help="Deprecated and can safely be removed",
        nargs="?",  # Makes it optional
        default=None,
    )
    parser.add_argument(
        "ert_username",
        type=str,
        help="Deprecated and can safely be removed",
        nargs="?",  # Makes it optional
        default=None,
    )
    parser.add_argument(
        "--sumo_env",
        type=str,
        help="Deprecated and can safely be removed",
        default=None,
    )
    parser.add_argument(
        "--verbosity", type=str, help="Set log level", default="WARNING"
    )
    return parser


def _parse_config(args: argparse.Namespace) -> WorkflowConfig:
    """Convert parsed args to config.

    Also handles deprecations."""
    if args.ert_casename:
        warnings.warn(
            "The argument 'ert_casename' is deprecated. It is no "
            "longer used and can safely be removed.",
            FutureWarning,
        )
    if args.ert_username:
        warnings.warn(
            "The argument 'ert_username' is deprecated. It is no "
            "longer used and can safely be removed.",
            FutureWarning,
        )
    if args.sumo_env:
        warnings.warn(
            "The argument 'sumo_env' is ignored and can safely be removed.",
            FutureWarning,
        )
        if args.sumo_env != "prod" and os.getenv("SUMO_ENV") is None:
            raise ValueError(
                "Setting sumo environment through argument input is not allowed. "
                "It must be set as an environment variable SUMO_ENV"
            )

    return WorkflowConfig(
        casepath=args.casepath,
        ert_config_path=args.ert_config_path,
        global_variables_path=args.global_variables_path,
        register_on_sumo=args.sumo,
        verbosity=args.verbosity,
    )


class WfCreateCaseMetadata(ert.ErtScript):
    """A class with a run() function that can be registered as an ERT plugin.

    This is used for the ERT workflow context. It is prefixed 'Wf' to avoid a
    potential naming collisions in fmu-dataio."""

    def run(
        self,
        workflow_args: list[str],
        ensemble: ert.Ensemble,
        run_paths: ert.Runpaths,
    ) -> None:
        # pylint: disable=no-self-use
        """Parse arguments and run the workflow."""
        parser = get_parser()
        args = parser.parse_args(workflow_args)
        _run_workflow(args, ensemble, run_paths)


def _run_workflow(
    args: argparse.Namespace, ensemble: ert.Ensemble, run_paths: ert.Runpaths
) -> None:
    """Main workflow entry point."""
    workflow_config = _parse_config(args)
    workflow_config.validate()
    logger.setLevel(args.verbosity)

    # TODO: Load to validated dict and pass to case object
    global_config_dict = _load_global_config(workflow_config.global_config_path)
    try:
        global_config = global_configuration.GlobalConfiguration.model_validate(
            global_config_dict
        )
    except ValidationError as e:
        global_configuration.validation_error_warning(e)
        raise

    metadata_path = create_case_metadata(workflow_config, global_config_dict)
    logger.debug(f"Case metadata exported to {metadata_path}")

    parameters_path = export_ert_parameters(
        ensemble, run_paths, workflow_config.casepath, global_config
    )
    logger.debug(f"Parameters exported to {parameters_path}")


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
