"""Export a surface with dataio based on surface that is already on disk

I.e. what we do is actually add metadata and store in the right place

The input maps is poro_average.grid
"""
from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

import fmu.dataio as dataio

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

FILES = {
    "poro": Path("../output/maps/props") / "poro_average.gri",
    "depth": Path("../output/maps/structure/") / "topvolantis--ds_extract_geogrid.gri",
}


def main():
    """Emulate map export during FMU runs.

    In the FMU workflow, individual jobs will be responsible for dumping data to the
    disk. In this example, we are emulating this to obtain the same effect.
    """

    print("Export a porosity average map")
    surf = xtgeo.surface_from_file(FILES["poro"])
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

    # -------------------------------------

    print("export a depth surface")
    surf = xtgeo.surface_from_file(FILES["depth"])
    print(f"Average value of map is {surf.values.mean()}")

    ed = dataio.ExportData(
        config=CFG,
        name="topvolantis",
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
