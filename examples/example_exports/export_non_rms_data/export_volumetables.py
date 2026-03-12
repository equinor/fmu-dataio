"""Re-export already exported volume tables for Sumo."""

from pathlib import Path

import pandas as pd
from fmu.config import utilities as ut

from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

VOL_DIR = Path("../output/volumes/")
VOL_FILES = ["geogrid_vol.csv", "simgrid_vol.csv"]


def load_volume_df(vol_file):
    """Loads an already exported volumes table into a Pandas dataframe."""
    fname = VOL_DIR / vol_file
    return pd.read_csv(fname)


def export_volumes(df, grid_name):
    """Re-export the volume table with metadata for Sumo."""

    export_data = ExportData(
        name=grid_name,
        config=CFG,
        content="volumes",
        unit="m3",
        tagname="volumes",
        workflow="Volume calculation",
    )

    out_path = export_data.export(df)
    print(f"Exported volume table for {grid_name} to {out_path}")


def main():
    print("\nExporting volume tables and metadata...")

    for vol_file in VOL_FILES:
        # Converts a file name like "geogrid_vol.csv" --> "geogrid"
        grid_name = vol_file.replace("_vol.csv", "")

        df = load_volume_df(vol_file)
        export_volumes(df, grid_name)

    print("Done exporting volume tables and metadata.")


if __name__ == "__main__":
    main()
