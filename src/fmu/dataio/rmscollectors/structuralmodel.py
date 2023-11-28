"""Contains class RmsStructuralModel and related functions"""
import logging
from dataclasses import dataclass
from fmu.dataio.rmscollectors import utils
from xtgeo import points_from_roxar, surface_from_roxar, polygons_from_roxar
from fmu.dataio import ExportData
from fmu.config.utilities import yaml_load

logging.basicConfig(level="DEBUG")
logger = logging.getLogger("structuralmodel")


def _extract_fault_info(job_parameters):
    """Extract fault information

    Args:
        job_parameters (dict): the job arguments

    Returns:
        dict: extracted fault information
    """
    fault_dict = {}
    for i, fault_name in enumerate(job_parameters["FaultNames"]):
        fault_dict[fault_name] = {
            "displacement": job_parameters["UseDisplacement"][i],
            "older_than": job_parameters["OlderThan"][i],
            "constraints": job_parameters["FaultConstraints"][i],
        }
    return fault_dict


def _extract_input_types(job_parameters):
    input_data = job_parameters["InputData"]
    representations = [rep[-1] for rep in input_data]
    return representations


def _extract_surf_info(job_parameters, representations):
    """Extract surface information

    Args:
        job_parameters (dict): the job arguments

    Returns:
        dict: extracted surface information
    """
    surface_stack = {}
    for i, surf_info in enumerate(job_parameters["Layer Model"]):
        logger.debug(surf_info["ZoneLogCodes"])
        try:
            for surf in surf_info["Horizon Parameters"]:
                hor_info = surf["Horizon"]
                representation_usage = {}

                for i, data_usage in enumerate(surf["InputDataUsage"]):
                    representation_usage[representations[i]] = data_usage
                iso_input = surf["Isochore Input"][0]
                if iso_input["IsochoreSurface"]:
                    iso = iso_input["IsochoreSurface"]
                else:
                    iso = iso_input["ConstantThickness"]
                surface_stack[hor_info[-1]] = {
                    "stype": hor_info[0].lower(),
                    "isochore": iso,
                    "xy-increment": surf["GridXYIncrement"],
                    "soft-smoothing-range": surf["SoftDataSmoothingRange"],
                    "hard-smoothing-range": surf["HardDataCorrectionRange"],
                    "conform-smoothing-range": surf["ConformalCorrectionRange"],
                    "representations": representation_usage,
                }
        except KeyError:
            logger.debug("No Horizon Parameters section present for level %s", i)
    logger.debug("Returning %s", surface_stack)
    return surface_stack


def export_surfaces(project, surface_info, config_path):
    export_paths = []
    config = yaml_load(config_path)
    exd = ExportData(config=config, content="depth")
    for surf_name, specs in surface_info.items():
        for rep_name in specs["representations"]:
            print("Exporting representation %s for %s", rep_name, surf_name)
            for rox_reader in [
                points_from_roxar,
                polygons_from_roxar,
                surface_from_roxar,
            ]:
                try:
                    obj = rox_reader(project, surf_name, rep_name)
                    obj_path = exd.export(obj, name=surf_name, tagname=rep_name)
                    export_paths.append(obj_path)
                    continue
                except TypeError:
                    logger.info(
                        "Trying to read %s %s with %s failed",
                        surf_name,
                        rep_name,
                        rox_reader.__name__,
                    )
        return export_paths


@dataclass
class RmsStructuralModel:
    project: str
    structural_model_name: str
    horizon_model_name: str

    def __post_init__(self):
        self.project = utils._get_project(self.project, True)
        sm = self.project.structural_models[self.structural_model_name]
        hmodel = sm.horizon_models[self.horizon_model_name]
        geom = hmodel.get_geometry()
        self.horizons = geom.horizons
        self.faults = geom.faults


@dataclass
class RmsStructuralModelJob:
    """Class for exporting data related to structural model"""

    project: str
    structural_model_name: str
    horizon_model_name: str
    job_name: str

    def __post_init__(self):
        """Initialize what is not initialized upfront"""
        self.project = utils._get_project(self.project, True)
        self.params = utils.get_job_arguments(
            ["Structural models", self.structural_model_name, self.horizon_model_name],
            "Horizon Modeling",
            self.job_name,
        )
        self.representations = _extract_input_types(self.params)
        self.faults = _extract_fault_info(self.params)
        self.surfaces = _extract_surf_info(self.params, self.representations)
        self.horizon_model = RmsStructuralModel(
            self.project, self.structural_model_name, self.horizon_model_name
        )

    @property
    def fault_names(self):
        """Return fault keys as list"""
        return list(self.faults.keys())

    @property
    def surface_names(self):
        """Return surface keys as list"""
        return list(self.surfaces.keys())
