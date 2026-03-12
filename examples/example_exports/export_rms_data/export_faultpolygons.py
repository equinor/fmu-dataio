"""Export fault lines polygons.

This example contains two cases of exporting: directly from the RMS project or from
already exported files. These two cases are indicated with comments where appropriate.
"""

from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

HORIZON_NAMES = CFG["rms"]["horizons"]["TOP_RES"]

# If inside RMS, set the polygon category.
RMS_POL_CATEGORY = "GL_faultlines_extract_postprocess"

# If re-exporting already exported files for Sumo, set the directory where the files
# have been exported.
POL_DIR = Path("../output/polygons")


def export_fault_lines():
    """Re-export fault lines polygons with metadata in two formats."""

    # Export both csv (keeping xtgeo column names) and irap text format The difference
    # bewtween "csv" and "csv|xtgeo" is that the latter will keep xtgeo column names
    # as-is while "csv" will force column names to "X Y Z ID"
    for fmt in ["csv|xtgeo", "irap_ascii"]:
        ExportData.polygons_fformat = fmt
        export_data = ExportData(
            config=CFG,
            content="fault_lines",
            unit="m",
            tagname="faultlines",
            workflow="rms structural model",
        )

        for name in HORIZON_NAMES:
            # RMS: read the polygon directly from RMS
            # poly = xtgeo.polygons_from_roxar(project, name, RMS_POL_CATEGORY)

            # From an already exported polygon
            pol_file = POL_DIR / f"{name.lower()}.pol"
            poly = xtgeo.polygons_from_file(pol_file)
            poly.name = name

            export_data.export(poly)


def main():
    print("\nExporting fault lines polygons and metadata...")
    export_fault_lines()
    print("Done exporting fault lines polygons and metadata.")


if __name__ == "__main__":
    main()
