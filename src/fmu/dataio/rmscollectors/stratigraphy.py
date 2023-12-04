import logging
from fmu.config.utilities import yaml_load

logger = logging.getLogger(__file__)


def add_to_strat(strat_dict, name, strat):
    """Add stratigraphic level, and top and base relations

    Args:
        strat_dict (dict): the stratigraphy dictionary
        name (str): name of zone
        strat (dict): the dictionary with official names,
    """
    if name not in strat_dict:
        strat_dict[name] = {"top_of": [], "base_of": []}
        try:
            strat_dict[name]["official"] = strat[name]["name"]
        except KeyError:
            print(f"{name} not part of stratigraphy")


def define_init_stratigraphy(project):
    """Construct inital stratigraphy from rms

    Args:
        project (str or roxar.project): rms project to read from

    Returns:
        dict: the stratigraphy with initial levels
    """
    stratigraphy = {}
    for zone in project.zones:
        stratigraphy[zone.name] = {
            "above": zone.horizon_above.name,
            "below": zone.horizon_below.name,
        }
    return stratigraphy


def define_full_stratigraphy(
    project, config_path="../../fmuconfig/output/global_variables.yml"
):
    """Construct full stratigraphy with relations

    Args:
        project (str or rms project): rms project to read from
        config_path (str, optional): config file with official names of surfaces.
        Defaults to "../../fmuconfig/output/global_variables.yml".

    Returns:
        dict: the relations dictionary
    """
    try:
        cfg = yaml_load(config_path)
        strat = cfg["stratigraphy"]
    except KeyError:
        logger.warning("No stratigraphy section in config")
        strat = {}
    except OSError:
        logger.warning("No config file at %s", config_path)
        strat = {}
    init_stratigraphy = define_init_stratigraphy(project)
    surf_stratigraphy = {}
    for surf_name, relations in init_stratigraphy.items():
        above_name = relations["above"]
        below_name = relations["below"]
        add_to_strat(surf_stratigraphy, above_name, strat)
        add_to_strat(surf_stratigraphy, below_name, strat)

        surf_stratigraphy[above_name]["top_of"].append(surf_name)
        surf_stratigraphy[below_name]["base_of"].append(surf_name)

    logger.debug(surf_stratigraphy)
    return surf_stratigraphy
