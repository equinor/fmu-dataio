"""Export a surface with dataio based on surface that is already on disk

I.e. what we do is actually add metadata and store in the right place

The input maps is poro_average.grid
"""
from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

import fmu.dataio as dataio

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")


INPUT_FOLDER = Path("../output/maps/props")
FILE = "poro_average.gri"


def main():
    """Exporting maps from clipboard"""

    surf = xtgeo.surface_from_file(INPUT_FOLDER / FILE)
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


if __name__ == "__main__":
    main()
    print("That's all")
