"""Export polygons of two types: field regions and field outlines."""

from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

# If re-exporting already exported files for Sumo, set the directory where the files
# have been exported.
POL_DIR = Path("../output/polygons")


def export_field_region():
    """Re-export a field region polygon with metadata."""

    # The difference bewtween "csv" and "csv|xtgeo" is that the latter will keep
    # xtgeo column names as-is while "csv" will force column names to "X Y Z ID"
    export_data = ExportData(
        config=CFG,
        content="field_region",
        content_metadata={"id": 1},
        unit="m",
        is_prediction=False,
        tagname="polygons_field_region",
        workflow="rms structural model",
        polygons_fformat="csv|xtgeo",
    )

    horizon_name = "BaseVolantis"
    pol_file = POL_DIR / f"{horizon_name.lower()}.pol"

    poly = xtgeo.polygons_from_file(pol_file)
    poly.name = horizon_name

    out_path = export_data.export(poly)

    print(f"Exported field region for {horizon_name} to {out_path}")


def export_field_outline():
    """Re-export a field outline polygon with metadata."""

    export_data = ExportData(
        config=CFG,
        content="field_outline",
        content_metadata={"contact": "goc"},
        unit="m",
        tagname="polygons_field_outline",
        workflow="rms structural model",
        polygons_fformat="csv|xtgeo",
    )

    horizon_name = "BaseVolantis"
    pol_file = POL_DIR / f"{horizon_name.lower()}.pol"

    poly = xtgeo.polygons_from_file(pol_file)
    poly.name = horizon_name

    out_path = export_data.export(poly)
    print(f"Exported field outline for {horizon_name} to {out_path}")


def main():
    print("\nExporting polygons and metadata...")
    export_field_region()
    export_field_outline()
    print("Done exporting polygons and metadata.")


if __name__ == "__main__":
    main()
