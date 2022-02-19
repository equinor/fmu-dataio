"""Export a surface with dataio based on surface that is already on disk

I.e. what we do is actually add metadata and store in the right place

The input maps is poro_average.grid
"""
from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

import fmu.dataio as dataio

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")


FILES = [
    "../output/maps/props/poro_average.gri",
    "../output/maps/structure/topvolantis--ds_extract_geogrid.gri",
]


def main():
    """Exporting maps from RMS"""

    # Export a property map

    surf = xtgeo.surface_from_file(FILES[0])
    print(f"Average value of map is {surf.values.mean()}")

    ed = dataio.ExportData(
        config=CFG,
        name="noname_here",
        unit="fraction",
        vertical_domain={"depth": "msl"},
        content="property",
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="average_poro",
        workflow="rms property model",
    )
    fname = ed.export(surf, name="all")  # note that 'name' here will be used
    print(f"File name is {fname}")

    # Export a structural map

    print("Export a depth map...")
    surf = xtgeo.surface_from_file(FILES[1])
    print(f"Average value of map is {surf.values.mean()}")

    ed = dataio.ExportData(
        config=CFG,
        name="TopVolantis",  # will be translated to strat column name
        unit="m",
        vertical_domain={"depth": "msl"},
        content="depth",
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="ds_extract_geogrid",
        workflow="rms structural model",
    )
    fname = ed.export(surf)
    print(f"File name is {fname}")


if __name__ == "__main__":
    main()
    print("That's all")
