"""Contains class RmsStructuralModel and related functions"""
import logging
from dataclasses import dataclass
from fmu.dataio.rmscollectors import utils

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


@dataclass
class RmsStructuralModel:
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
        self.faults = _extract_fault_info(self.params)
        self.surfaces = _extract_surf_info(self.params)

    @property
    def fault_names(self):
        """Return fault keys as list"""
        return list(self.faults.keys())

    @property
    def surface_names(self):
        """Return surface keys as list"""
        return list(self.surfaces.keys())
