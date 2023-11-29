import logging
from dataclasses import dataclass
from xtgeo import grid_from_roxar
from fmu.dataio.rmscollectors import utils
from fmu.dataio.rmscollectors.structuralmodel import RmsStructuralModel

logging.basicConfig(level="DEBUG")
logger = logging.getLogger("__file__")


def check_if(parameters, keyword, i=-1):
    """Check if specific keyword is equal to str false

    Args:
        parameters (dict): the job parameters
        keyword (str): keyword in parameters

    Returns:
        bool: true if keyword is "false", else false
    """
    if i < 0:
        bool_value = parameters[keyword]
        print_key = keyword
    else:
        bool_value = parameters[keyword][i]
        print_key = f"{keyword}[{i}]"
    logger.debug("%s %s, bool: %s", print_key, bool_value, isinstance(bool_value, bool))

    return bool_value


def _get_general_settings(parameters):
    """Get general setting for grid

    Args:
        parameters (dict): job parameters

    Returns:
        _type_: _description_
    """
    general = {
        "repeatsections_allowed": check_if(parameters, "RepeatSections"),
        "regularized_grid": check_if(parameters, "RegularizedGrid"),
        "vertical_boundary": check_if(parameters, "VerticalBoundary"),
        "juxtaposition_correction": check_if(parameters, "JuxtapositionCorrection"),
        "grid_clipped": check_if(parameters, "ClipGrid"),
    }
    return general


def _get_horizon_model(parameters):
    """Get information about horizon model used

    Args:
        parameters (dict): job parameters

    Returns:
        dict: dictionary with structural model info
    """
    horizon_section = parameters["HorizonModel"]
    # Stupid implemented below because when running in jupyter notebook
    # an empty entry is added to this section
    while horizon_section[0] == "":
        horizon_section.pop(0)
    logger.debug("Will extract info from Horizon section: %s", horizon_section)
    horizon_info = {
        "structural_model": horizon_section[1],
        "horizon_model": horizon_section[2],
    }
    logger.debug("After extraction: %s", horizon_info)
    return horizon_info


def _get_zone_info(parameters):
    """Extract information about zones

    Args:
        parameters (dict): job parameters

    Returns:
        dict: digested zone info
    """
    zone_names = parameters["ZoneNames"]
    zone_info = {}
    for i, zone_name in enumerate(zone_names):
        if parameters["ConformalMode"] == "0":
            griding_type = "proportional"
        elif parameters["ConformalMode"] == "1":
            griding_type = "top_conformable"
        else:
            griding_type = "base_conformable"

        sampled = check_if(parameters, "SampledHorizons", i)
        air = check_if(parameters, "AirHorizons", i)
        if not griding_type == "proportional":
            truncated = check_if(parameters, "Truncated", i)
        else:
            truncated = False

        if check_if(parameters, "UsedHorizons", i):
            top = "from_structural_model"
        else:
            top = parameters["TopSurfaces"][i]

        zone_info[zone_name] = {
            "top_from": top,
            "gridding": griding_type,
            "sampled": sampled,
            "air_interpretation": air,
            "truncated_top": truncated,
        }
    return zone_info


def _get_fault_info(parameters):
    """Get information about the faults

    Args:
        parameters (dict): job parameters

    Returns:
        dict: key, fault name, value either stairstepped or amount of pillar adjustment
    """
    fault_section = parameters["FaultStateMap"]
    fault_info = {}
    for name, definition in fault_section:
        if definition == "-1":
            definition = "stairstepped"
        else:
            definition = {"pillar_adjustment": definition}
        fault_info[name] = definition
    return fault_info


def _get_grid_dimensions(parameters):
    """Extract info about grid dimensions

    Args:
        parameters (dict): the job parameters

    Returns:
        dict: grid dimensions info
    """
    grid_dimensions = {
        "origin": {"x": parameters["Origin"][0], "y": parameters["Origin"][1]},
        "length": {"x": parameters["XLength"], "y": parameters["YLength"]},
        "rotation": parameters["Rotation"],
    }
    if parameters["UseXInc"]:
        xinc = parameters["XInc"]
    else:
        xinc = round(parameters["XLength"] / parameters["XCells"])
    if parameters["UseYInc"]:
        yinc = parameters["YInc"]
    else:
        yinc = round(parameters["YLength"] / parameters["YCells"])

    grid_dimensions["increment"] = {"x": xinc, "y": yinc}
    return grid_dimensions


@dataclass
class RmsGrid:
    """Class for exporting data Grid"""

    project: str
    grid_name: str
    job_name: str
    params: dict = None

    def __post_init__(self):
        """Initialize what is not initialized upfront"""
        self.project = utils._get_project(self.project, True)

        self.params = utils.get_job_arguments(
            ["Grid models", self.grid_name, "Grid"], "Create Grid", self.job_name
        )
        self.dimensions = _get_grid_dimensions(self.params)
        self.general_settings = _get_general_settings(self.params)
        self.based_on = _get_horizon_model(self.params)
        self.faults = _get_fault_info(self.params)
        self.zones = _get_zone_info(self.params)
        self.horizon_model = RmsStructuralModel(
            self.project,
            self.based_on["structural_model"],
            self.based_on["horizon_model"],
        )
        self.grid = grid_from_roxar(self.project, self.grid_name)

    @property
    def fault_names(self):
        """Return keys of faults attribute as list"""
        return list(self.faults.keys())

    @property
    def zone_names(self):
        """Return keys of zones attribute as list"""
        return list(self.zones.keys())

    @property
    def horizon_names(self):
        """Return horizon_model horizon names

        Returns:
        list: names of horizons for structural model
        """
        return self.horizon_model.horizons["Name"]
