"""Create FMU case metadata and register case on Sumo.

FMU ECOSYSTEM  is responsible for adding this PRE_SIMULATION workflow to the Ert
config. Users should not configure it themselves.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Final

import ert

from fmu.dataio._export import ExportConfig
from fmu.dataio._interfaces import SumoUploaderInterface
from fmu.dataio._metadata import generate_metadata
from fmu.dataio._workflows.case._config import CaseWorkflowConfig
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import Content, FMUContext
from fmu.datamodels.standard_results.enums import (
    ModelStratigraphy,
    StandardResultName,
)
from fmu.settings import (
    ProjectFMUDirectory,
    find_nearest_fmu_directory,
    get_fmu_directory,
)

from .._utils import validate_casepath
from ._config import PreSimulationConfig
from ._mappings import get_stratigraphy_mappings_table, get_wellbore_mappings_table
from ._model_stratigraphy import (
    get_model_stratigraphy_horizons_table,
    get_model_stratigraphy_zones_table,
)
from ._parameters import get_ert_parameters_table
from .export_case_metadata import ExportCaseMetadata

if TYPE_CHECKING:
    from ert.runpaths import Runpaths as ErtRunpaths
    from ert.storage import Ensemble as ErtEnsemble


logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

DESCRIPTION = (
    "FMU ECOSYSTEM is responsible for adding this PRE_SIMULATION workflow to the Ert "
    "config. Users should not configure it themselves."
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
    workflow_config: PreSimulationConfig | CaseWorkflowConfig,
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


def _queue_stratigraphy_mappings(
    ensemble_name: str,
    workflow_config: PreSimulationConfig | CaseWorkflowConfig,
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
        .standard_result(StandardResultName.stratigraphy_mapping)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_model_stratigraphy_horizons(
    ensemble_name: str,
    workflow_config: PreSimulationConfig | CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export model stratigraphy horizons using fmu-dataio."""
    assert workflow_config.fmu_dir is not None

    table = get_model_stratigraphy_horizons_table(workflow_config.fmu_dir)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.stratigraphy)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=ModelStratigraphy.HorizonsColumns.index_columns())
        .file_config(name=StandardResultName.model_stratigraphy_horizons.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .standard_result(StandardResultName.model_stratigraphy_horizons)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_model_stratigraphy_zones(
    ensemble_name: str,
    workflow_config: PreSimulationConfig | CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Export model stratigraphy zones using fmu-dataio."""
    assert workflow_config.fmu_dir is not None

    table = get_model_stratigraphy_zones_table(workflow_config.fmu_dir)
    if table is None:
        return

    export_config = (
        ExportConfig.builder()
        .content(Content.stratigraphy)
        .access(Classification.internal, rep_include=False)
        .table_config(table_index=ModelStratigraphy.ZonesColumns.index_columns())
        .file_config(name=StandardResultName.model_stratigraphy_zones.value)
        .global_config(workflow_config.global_config)
        .run_context(
            fmu_context=FMUContext.ensemble,
            ensemble_name=ensemble_name,
            casepath=workflow_config.casepath,
        )
        .standard_result(StandardResultName.model_stratigraphy_zones)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _queue_wellbore_mappings(
    ensemble_name: str,
    workflow_config: PreSimulationConfig | CaseWorkflowConfig,
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
        .standard_result(StandardResultName.wellbore_mapping)
        .build()
    )
    metadata = generate_metadata(export_config, table)
    sumo_uploader.queue_table(table, metadata)


def _upload_files_to_sumo(
    ensemble: ErtEnsemble,
    run_paths: ErtRunpaths,
    workflow_config: PreSimulationConfig | CaseWorkflowConfig,
    sumo_uploader: SumoUploaderInterface,
) -> None:
    """Establishes a case on Sumo, uploading initial case and ensemble data as well.

    Any tables already queued on ``sumo_uploader`` by the caller are uploaded in the
    same batch. Observations are intentionally not queued here; they belong to the
    legacy WF_CREATE_CASE_METADATA workflow and, in the future, a post-simulation
    workflow.
    """
    ensemble_name = _get_ensemble_name(ensemble, run_paths, workflow_config.casepath)

    _queue_ert_parameters(ensemble, ensemble_name, workflow_config, sumo_uploader)

    if workflow_config.fmu_dir:
        _queue_model_stratigraphy_horizons(
            ensemble_name, workflow_config, sumo_uploader
        )
        _queue_model_stratigraphy_zones(ensemble_name, workflow_config, sumo_uploader)
        _queue_stratigraphy_mappings(ensemble_name, workflow_config, sumo_uploader)
        _queue_wellbore_mappings(ensemble_name, workflow_config, sumo_uploader)

    sumo_uploader.upload()


def _run_workflow(
    ensemble: ErtEnsemble,
    workflow_config: PreSimulationConfig,
) -> None:
    """Main workflow entry point."""

    case_metadata_path = ExportCaseMetadata.from_workflow_config(
        workflow_config
    ).export()
    logger.debug(f"Case metadata exported to {case_metadata_path}")

    sumo_uploader = SumoUploaderInterface.from_new_case(Path(case_metadata_path))
    _upload_files_to_sumo(
        ensemble=ensemble,
        run_paths=workflow_config.run_paths,
        workflow_config=workflow_config,
        sumo_uploader=sumo_uploader,
    )


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


class WfFmuPreSimulation(ert.ErtScript):
    # Older Ert versions override the registered description with the class docstring.
    __doc__ = DESCRIPTION

    # Ensure ERT execution stops if the workflow fails
    stop_on_fail = True

    def run(
        self,
        ensemble: ErtEnsemble,
        run_paths: ErtRunpaths,
    ) -> None:
        """Parse arguments and run the workflow."""

        sumo_casepath = run_paths.substitutions.get("<SUMO_CASEPATH>")
        if not sumo_casepath:
            raise ValueError("Define <SUMO_CASEPATH> in the Ert config")

        casepath = validate_casepath(Path(sumo_casepath))
        fmu_dir = _copy_fmu_directory(casepath)

        cfg = PreSimulationConfig.build_presim_config(
            run_paths=run_paths, casepath=casepath, fmu_dir=fmu_dir
        )

        _run_workflow(ensemble, cfg)


@ert.plugin(name="fmu_dataio")
def ertscript_workflow(config: ert.WorkflowConfigs) -> None:
    """Internal pre-simulation workflow for FMU ECOSYSTEM."""
    config.add_workflow(
        WfFmuPreSimulation,
        "WF_FMU_PRE_SIMULATION",
        description=DESCRIPTION,
        category="export",
    )
