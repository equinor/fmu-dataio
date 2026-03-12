"""Re-export already exported surfaces with metadata."""

from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

PORO_FILE = Path("../output/maps/props/poro_average.gri")
DEPTH_FILE = Path("../output/maps/structure/topvolantis--ds_extract_geogrid.gri")


def export_porosity_average_map():
    """Emulate map export during FMU runs.

    In the FMU workflow, individual jobs will be responsible for dumping data to disk.
    In this example, we are emulating this to obtain the same effect.
    """

    print("Export a porosity average map and property surface metadata.")
    poro_surf = xtgeo.surface_from_file(PORO_FILE)
    print(f"Average value of map is {poro_surf.values.mean()}")

    export_data = ExportData(
        config=CFG,
        name="all",
        unit="fraction",
        content="property",
        content_metadata={"attribute": "porosity", "is_discrete": False},
        tagname="average_poro",
        workflow="rms property model",
    )

    out_path = export_data.export(poro_surf)
    print(f"Exported to file {out_path}")


def export_depth_surface():
    """Export a depth surface map with metadata."""

    print("Export a depth surface")
    surf = xtgeo.surface_from_file(DEPTH_FILE)
    print(f"Average value of map is {surf.values.mean()}")

    export_data = ExportData(
        config=CFG,
        name="topvolantis",
        unit="m",
        content="depth",
        tagname="ds_extract_geogrid",
        workflow="rms structural model",
    )

    out_path = export_data.export(surf)
    print(f"Exported to file {out_path}")


def export_fluid_contact_surface():
    """Export metadata for fluid contact surface"""

    print("Export fluid contact surface map and metadata")

    # For simplicity, the depth surface map is reused as input.
    # For a real case, use a fluid contact surface as input.
    fluid_contact_surf = xtgeo.surface_from_file(DEPTH_FILE)

    export_data = ExportData(
        config=CFG,
        name="surface_fluid_contact",
        unit="m",
        content="fluid_contact",
        content_metadata={"contact": "fwl"},
        tagname="",
        workflow="rms structural model",
    )

    out_file = export_data.export(fluid_contact_surf)
    print(f"Exported to file {out_file}")


def export_seismic_amplitude_surface():
    """Export metadata for a seismic amplitude surface"""

    print("Export seismic amplitude surface map and metadata.")

    # For simplicity, the depth surface map is reused as input.
    # For a real case, use a seismic amplitude surface as input.
    seismic_attribute_surf = xtgeo.surface_from_file(DEPTH_FILE)

    export_data = ExportData(
        config=CFG,
        name="surface_seismic_amplitude",
        unit="m",
        content="seismic",
        content_metadata={
            "attribute": "amplitude",
            "calculation": "mean",
            "zrange": 12.0,
            "stacking_offset": "0-15",
        },
        timedata=[["20201028", "base"], ["20201028", "monitor"]],
        tagname="",
        workflow="rms structural model",
    )

    out_file = export_data.export(seismic_attribute_surf)
    print(f"Exported to file {out_file}")


def main():
    print("\nExporting surface maps and metadata...")
    export_porosity_average_map()
    export_depth_surface()
    export_fluid_contact_surface()
    export_seismic_amplitude_surface()
    print("Done exporting surface maps and metadata.")


if __name__ == "__main__":
    main()
