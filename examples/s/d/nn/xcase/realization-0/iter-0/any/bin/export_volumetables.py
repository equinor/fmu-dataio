"""Read volume table from RMS or file and export to CSV for SUMO.

In this example there is switch, IN_ROXAR which is set to True if using it inside
RMS (to demostrate how volume tables can be fetched via Roxar API).

For the file case, CSV files are read from disk. The dataio function is the same.
"""

import logging
import pathlib

import pandas as pd

import fmu.dataio
from fmu.config import utilities as ut

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")


VFOLDER = "../output/volumes/"
VFILES = ["geogrid_vol.csv", "simgrid_vol.csv"]

TAGNAME = "volumes"


def volume_as_dataframe_files(vfile):
    """Read volume (CSV files) and return dataframe."""

    # "geogrid_vol.csv" --> "geogrid" etc
    gridname = vfile.replace("_vol.csv", "")

    fname = pathlib.Path(VFOLDER) / vfile

    dframe = pd.read_csv(fname)
    return dframe, gridname


def export_dataio(df, gridname):
    """Get the dataframe and export to SUMO via dataio."""

    exp = fmu.dataio.ExportData(
        name=gridname,
        config=CFG,
        content="volumes",
        unit="m",
        is_prediction=True,
        is_observation=False,
        tagname=TAGNAME,
        workflow="Volume calculation",
    )

    out = exp.export(df)
    print(f"Exported volume table for {gridname} to {out}")


if __name__ == "__main__":
    for vfile in VFILES:
        df, gridname = volume_as_dataframe_files(vfile)
        export_dataio(df, gridname)
