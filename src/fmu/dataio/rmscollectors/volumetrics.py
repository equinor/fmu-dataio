"""Contains class RmsInplaceVolumes and related functions"""
import logging
from dataclasses import dataclass
import pandas as pd
from xtgeo import gridproperty_from_roxar, surface_from_roxar
from fmu.dataio import ExportData
from fmu.config.utilities import yaml_load
from fmu.dataio.rmscollectors import utils

logging.basicConfig(level="DEBUG")
logger = logging.getLogger("Inplace")

RENAME_VOLUMES = {
    "Proj. real.": "REAL",
    "Zone": "ZONE",
    "Segment": "REGION",
    "Boundary": "LICENSE",
    "Facies": "FACIES",
    "BulkOil": "BULK_OIL",
    "NetOil": "NET_OIL",
    "PoreOil": "PORV_OIL",
    "HCPVOil": "HCPV_OIL",
    "STOIIP": "STOIIP_OIL",
    "AssociatedGas": "ASSOCIATEDGAS_OIL",
    "BulkGas": "BULK_GAS",
    "PoreGas": "PORV_GAS",
    "HCPVGas": "HCPV_GAS",
    "GIIP": "GIIP_GAS",
    "AssociatedLiquid": "ASSOCIATEDOIL_GAS",
    "Bulk": "BULK_TOTAL",
    "Net": "NET_TOTAL",
    "Pore": "PORV_TOTAL",
}


def _define_prefixes(out_input):
    """Define prefixes that could be used

    Args:
        out_input (dict): dict with info to construct dict

    Returns:
        list: possible prefixes
    """
    prefix = out_input["Prefix"]
    if prefix != "":
        prefix = prefix + "_"
    prefixes = []
    if out_input["UseGas"]:
        prefixes.append(prefix + "Gas_")
    if out_input["UseOil"]:
        prefixes.append(prefix + "Oil_")
    logger.debug("\nReturning %s", prefixes)
    return prefixes


def _define_output(out_input, selectors):
    """Find maps and properties that can be exported

    Args:
        out_input (dict): the output params from job

    Returns:
        dict: info to use for exporting
    """
    logger.debug("\nExtracting output from %s", out_input)
    out_location = out_input["MapOutput"].lower()
    calculations = out_input["Calculations"]
    prefixes = _define_prefixes(out_input)
    properties = []
    maps = []
    for calculation in calculations:
        for prfx in prefixes:
            if calculation["CreateProperty"]:
                properties.append(prfx + calculation["Type"].lower())
            if calculation["CreateZoneMap"]:
                maps.append(prfx + calculation["Type"].upper())
    collated = {
        "maps": maps,
        "properties": properties,
        "map_location": out_location,
        "map_subfolders": selectors["Zone"]["filters"],
    }
    logger.debug("\nReturning %s", collated)
    return collated


def _define_variables(variables_input):
    """Get info about volumetric setup

    Args:
        variables_input (dict): dictionary with input setup

    Returns:
        dict: information to be used as metadata?
    """
    logger.debug("\nExtracting variables from %s", variables_input)
    var_definitions = {}
    variable_parameters = []
    for var_group in variables_input.values():
        for variable in var_group:
            name = variable["Name"]
            source = variable["InputSource"]
            table_values = variable["TableValues"]
            if variable["DataInput"]:
                propname = variable["DataInput"][0][-1]
                table_values = {"property": propname}
                if propname not in variable_parameters:
                    variable_parameters.append(propname)
            else:
                if source == "REGION_MODEL":
                    table_values = "hidden in region model"
            var_definitions[name] = {
                "applies": variable["InputType"],
                "values": table_values,
            }
    logger.debug("\nReturning %s", var_definitions)
    logger.debug("Additional properties are %s", variable_parameters)
    return var_definitions, variable_parameters


def _define_selectors(in_dict):
    """Find filters that can be applied

    Args:
        in_dict (dict): the input section from job parameters

    Returns:
        dict: the selectors found
    """
    logger.debug("\nExtracting selectors from %s", in_dict)
    possible_selectors = ["Zone", "Region", "Facies"]
    selectors = {}
    for key in possible_selectors[1:]:
        try:
            selectors[key] = {
                "filters": in_dict[f"Selected{key}Names"],
                "parameter": in_dict[f"{key}Property"][-1],
            }
        except IndexError:
            logger.warning("No selectors for %s", key)

    selectors.update(
        {
            "Zone": {"filters": in_dict["SelectedZoneNames"]},
            "parameter": "subgrids",
        }
    )
    logger.debug("\nReturning %s", selectors)
    return selectors


def get_volumetrics(project, table_name):
    """Get volumetrics table

    Args:
        project (str or roxar.project): the rms project to read from
        table_name (str): name of table in rms attached to job

    Returns:
        pd.DataFrame: the volumes
    """
    logger.debug("\nGetting volumes reading %s", table_name)
    try:
        volumes = pd.DataFrame.from_dict(
            project.volumetric_tables[table_name].get_data_table().to_dict()
        )
        logger.debug("Volumes before renaming %s", volumes.head(2))
        volumes.rename(columns=RENAME_VOLUMES, inplace=True)
        logger.debug("Volumes after renaming %s", volumes.head(2))
        volumes.drop("REAL", axis=1, inplace=True)
    except KeyError:
        logger.warning("No volume table attached")
        volumes = None
    return volumes


def _export_collection(project, collection, parent, job_name, config_path, **kwargs):
    export_paths = []
    config = yaml_load(config_path)
    exd = ExportData(config=config, parent=parent, **kwargs)
    for map_name in collection["maps"]:
        for folder_name in collection["map_subfolders"]:
            folder_name = f"Volumetrics_{job_name}/{folder_name}"
            logger.debug(
                "Fetching surface with name: %s, folder: %s", map_name, folder_name
            )
            try:
                surf = surface_from_roxar(
                    project, map_name, folder_name, stype=collection["map_location"]
                )
                surf_path = exd.export(
                    surf, name=map_name, tagname=job_name, content="property"
                )
                logger.debug("Exported %s", surf_path)

                export_paths.append(surf_path)
            except KeyError:
                logger.warning("No surface called %s", map_name)
    for property_name in collection["properties"]:
        logger.debug("Will be exporting %s for %s", property_name, parent)
        try:
            prop = gridproperty_from_roxar(project, parent, property_name)
            prop_path = exd.export(
                prop, name=property_name, tagname=job_name, content="property"
            )
            logger.debug("Exported %s", prop_path)
            export_paths.append(prop_path)
        except ValueError:
            logger.warning("No parameter called %s", property_name)
    try:
        if collection["table"] is not None:
            table_path = exd.export(
                collection["table"],
                parent=parent,
                name="volumes",
                tagname=job_name,
                content="volumetrics",
            )
            logger.debug("Exported %s", table_path)
            export_paths.append(table_path)
        else:
            logger.warning(
                "No volumes exported, have you forgot to select table option?"
            )
    except KeyError:
        logger.warning("No volume table attached")
    logger.info("Exported %i objects", len(export_paths))
    return export_paths


@dataclass
class RmsInplaceVolumes:
    """Class for exporting data related to volumetrics"""

    project: str
    grid_name: str
    job_name: str

    def __post_init__(self):
        """Initialize what is not initialized upfront"""
        self.project = utils._get_project(self.project, True)

        self.params = utils.get_job_arguments(
            ["Grid models", self.grid_name, "Grid"], "Volumetrics", self.job_name
        )
        self.input = self.params["Input"][0]
        self.output = self.params["Output"][0]
        self.variables = self.params["Variables"][0]

        self.report = get_volumetrics(self.params["Report"], self.project)
        self.selectors = _define_selectors(self.input)
        self.report_output = _define_output(self.output, self.selectors)
        self.input_variables, additional_props = _define_variables(self.variables)
        self.report_output["properties"].extend(additional_props)
        logger.debug(self.report_output["properties"])
        self.report_output["table"] = self.report

    def export(
        self, config_path="../../fmuconfig/output/global_variables.yml", **kwargs
    ):
        return _export_collection(
            self.project,
            self.report_output,
            self.grid_name,
            self.job_name,
            config_path,
            **kwargs,
        )
