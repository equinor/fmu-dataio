"""Export a surface with dataio based on surface that is already on disk

I.e. what we do is actually add metadata and store in the right place

The input maps is poro_average.grid
"""

import logging
from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu import dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

FILES = {
    "poro": Path("../output/maps/props") / "poro_average.gri",
    "depth": Path("../output/maps/structure/") / "topvolantis--ds_extract_geogrid.gri",
}


def export_porosity_average_map():
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


def export_depth_surface():
    """Export maps and metadata for a depth surface"""

    print("Export a depth surface")
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


def export_fluid_contact_surface():
    """Export metadata for fluid contact surface"""

    print("Export fluid contact surface map and metadata")

    # For simplicity, the depth surface map is reused as input.
    # For a real case, use a fluid contact surface as input.
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


def export_seismic_amplitude_surface():
    """Export metadata for a seismic amplitude surface"""

    print("Export seismic amplitude surface map and metadata.")

    # For simplicity, the depth surface map is reused as input.
    # For a real case, use a seismic amplitude surface as input.
    seismic_attribute_surf = xtgeo.surface_from_file(FILES["depth"])

    ed = dataio.ExportData(
        config=CFG,
        name="surface_seismic_amplitude",
        unit="m",
        vertical_domain="depth",
        domain_reference="msl",
        content="seismic",
        content_metadata={
            "attribute": "amplitude",
            "calculation": "mean",
            "zrange": 12.0,
            "stacking_offset": "0-15",
        },
        timedata=[["20201028", "base"], ["20201028", "monitor"]],
        is_prediction=True,
        is_observation=False,
        tagname="",
        workflow="rms structural model",
    )

    fname = ed.export(seismic_attribute_surf)
    print(f"Exported to file {fname}")


def main():
    print("\nExporting surface maps and metadata...")
    export_porosity_average_map()
    export_depth_surface()
    export_fluid_contact_surface()
    export_seismic_amplitude_surface()
    print("Done exporting surface maps and metadata.")


if __name__ == "__main__":
    main()
