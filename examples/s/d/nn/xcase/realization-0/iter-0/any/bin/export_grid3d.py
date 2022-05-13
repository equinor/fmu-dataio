"""Export 3D griddata with properties."""

import pathlib

import xtgeo
from fmu.config import utilities as ut

import fmu.dataio as dataio

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

FOLDER = pathlib.Path("../output/grids")
GFILE = "gg"
GNAME = "geogrid"
PROPS_SEISMIC = ["phit", "sw"]
PROPS_OTHER = ["klogh", "facies"]
VERBOSITY = "WARNING"


def export_geogrid_geometry():
    filename = (FOLDER / GFILE).with_suffix(".roff")
    grd = xtgeo.grid_from_file(filename)

    ed = dataio.ExportData(
        config=CFG,
        name=GNAME,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="",
        verbosity=VERBOSITY,
        workflow="rms structural model",
    )

    out = ed.export(grd)
    print(f"Stored grid as {out}")


def export_geogrid_parameters():
    """Export geogrid assosiated parameters based on user defined lists"""

    props = PROPS_SEISMIC + PROPS_OTHER

    print("Write grid properties...")
    for propname in props:
        filename = (FOLDER / (GFILE + "_" + propname)).with_suffix(".roff")
        prop = xtgeo.gridproperty_from_file(filename)
        ed = dataio.ExportData(
            name=propname,
            # parent={"name": GNAME},
            config=CFG,
            content="depth",
            unit="m",
            vertical_domain={"depth": "msl"},
            timedata=None,
            is_prediction=True,
            is_observation=False,
            verbosity=VERBOSITY,
            workflow="rms property model",
        )

        out = ed.export(prop)
        print(f"Stored {propname} as {out}")


if __name__ == "__main__":
    export_geogrid_geometry()
    export_geogrid_parameters()
    print("Done.")
