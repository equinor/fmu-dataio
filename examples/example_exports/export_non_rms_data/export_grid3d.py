"""Re-export 3D grids with properties."""

from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

OUT_DIR = Path("../output/grids")
GRID_FILE = "gg"
GRID_NAME = "geogrid"
PROPS_TO_EXPORT = ["phit", "sw", "klogh", "facies"]


def export_geogrid_geometry():
    """Export geogrid geometry.

    The geogrid must be exported first. Without exporting the geogrid first, we cannot
    link the exported grid properties to it. The properties are linked by knowing the
    file path the geogrid was exported to.
    """

    filename = OUT_DIR / f"{GRID_FILE}.roff"
    grd = xtgeo.grid_from_file(filename)

    export_data = ExportData(
        config=CFG,
        name=GRID_NAME,
        content="depth",
        unit="m",
        workflow="rms structural model",
    )

    out_grid_path = export_data.export(grd)
    print(f"Exported geogrid geometry to file {out_grid_path}")
    return out_grid_path


def export_geogrid_parameters(outgrid):
    """Export grid properties associated with the geogrid.

    By passing the path the geogrid was exported to we can link them to the geometry.
    The total list of properties that will be exported are set from the variable
    defined at the top.
    """

    for propname in PROPS_TO_EXPORT:
        filename = OUT_DIR / f"{GRID_FILE}_{propname}.roff"
        prop = xtgeo.gridproperty_from_file(filename)

        export_data = ExportData(
            config=CFG,
            name=propname,
            geometry=outgrid,
            content="property",
            content_metadata={"is_discrete": False},
            workflow="rms property model",
        )

        out_path = export_data.export(prop)
        print(f"Exported {propname} property geogrid to file {out_path}")


def main():
    print("\nExporting geogrids and metadata...")
    out_grid_path = export_geogrid_geometry()

    export_geogrid_parameters(out_grid_path)
    print("Done exporting geogrids and metadata.")


if __name__ == "__main__":
    main()
