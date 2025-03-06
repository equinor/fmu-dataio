"""Export a surface with dataio based on surface that is already on disk

I.e. what we do is actually add metadata and store in the right place

The input maps is poro_average.grid
"""

import logging
import os
from pathlib import Path

import xtgeo

from fmu import dataio
from fmu.config import utilities as ut

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = ut.yaml_load("../fmuconfig/output/global_variables.yml")

FILES = {
    "poro": Path("../output/maps/props") / "poro_average.gri",
    "depth": Path("../output/maps/structure/") / "topvolantis--ds_extract_geogrid.gri",
}


def main():
    """Emulate map export during FMU runs.

    In the FMU workflow, individual jobs will be responsible for dumping data to the
    disk. In this example, we are emulating this to obtain the same effect.
    """

    print("Export a porosity average map and property surface metadata.")
    poro_surf = xtgeo.surface_from_file(FILES["poro"])
    print(f"Average value of map is {poro_surf.values.mean()}")

    ed = dataio.ExportData(
        config=CFG,
        name="all",
        unit="fraction",
        vertical_domain="depth",
        domain_reference="msl",
        content="property",
        content_metadata={"is_discrete": False},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="average_poro",
        workflow="rms property model",
    )
    fname = ed.export(poro_surf)
    print(f"Exported to file {fname}")

    # -------------------------------------

    print("export a depth surface")
    surf = xtgeo.surface_from_file(FILES["depth"])
    print(f"Average value of map is {surf.values.mean()}")

    ed = dataio.ExportData(
        config=CFG,
        name="topvolantis",
        unit="m",
        vertical_domain="depth",
        domain_reference="msl",
        content="depth",
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="ds_extract_geogrid",
        workflow="rms structural model",
    )
    fname = ed.export(surf)
    print(f"Exported to file {fname}")

    # -------------------------------------    

    print("Export fluid contact surface map and metadata")
    fluid_contact_surf = xtgeo.surface_from_file(FILES["depth"])

    ed = dataio.ExportData(
        config=CFG,
        name="surface_fluid_contact",
        unit="m",
        vertical_domain="depth",
        domain_reference="msl",
        content="fluid_contact",
        content_metadata={"contact": "fwl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="",
        workflow="rms structural model",
    )
    fname = ed.export(fluid_contact_surf)
    print(f"Exported to file {fname}")

    # -------------------------------------

    print("Export seismic attribute surface map and metadata.")
    seismic_attribute_surf = xtgeo.surface_from_file(FILES["depth"])

    ed = dataio.ExportData(
        config=CFG,
        name="surface_seismic_amplitude",
        unit="m",
        vertical_domain="depth",
        domain_reference="msl",
        content="seismic",
        content_metadata={
            "attribute":"amplitude",
            "calculation": "mean",
            "zrange": 12.0,
            "stacking_offset": "0-15"
        },
        timedata=[["20201028", "base"], ["20201028", "monitor"]],
        is_prediction=True,
        is_observation=False,
        tagname="",
        workflow="rms structural model",
    )
    fname = ed.export(seismic_attribute_surf)
    print(f"Exported to file {fname}")


if __name__ == "__main__":
    print("\nExporting surface maps and metadata...")
    main()
    print("Done exporting surface maps and metadata.\n")
