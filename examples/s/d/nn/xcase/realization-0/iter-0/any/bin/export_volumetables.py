"""Read volume table from RMS or file and export to CSV for SUMO.

In this example there is switch, IN_ROXAR which is set to True if using it inside
RMS (to demostrate how volume tables can be fetched via Roxar API).

For the file case, CSV files are read from disk. The dataio function is the same.
"""
import pathlib
import pandas as pd
import fmu.dataio
from fmu.config import utilities as ut

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

IN_ROXAR = False

PRJ = None
if IN_ROXAR:
    PRJ = project  # type: ignore # noqa # pylint: disable=undefined-variable
    VTABLES = ["geogrid_volumes", "simgrid_volumes"]
else:
    VFOLDER = "../output/volumes/"
    VFILES = ["geogrid_vol.csv", "simgrid_vol.csv"]


TAGNAME = "volumes"
VERBOSITY = "WARNING"

# renaming columns from RMS to FMU standard
RENAMING = {
    "Proj. real.": "REALIZATION",
    "Zone": "ZONE",
    "Segment": "REGION",
    "BulkOil": "BULK_OIL",
    "PoreOil": "PORV_OIL",
    "HCPVOil": "HCPV_OIL",
    "STOIIP": "STOIIP_OIL",
    "AssociatedGas": "ASSOCIATEDGAS_OIL",
    "BulkGas": "BULK_GAS",
    "PoreGas": "PORV_GAS",
    "HCPVGas": "HCPV_GAS",
    "GIIP": "GIIP_GAS",
    "AssociatedLiquid": "ASSOCIATEDOIL_GAS",
    "Bulk": "BULK_TOTAL",
    "Pore": "PORV_TOTAL",
}


def volume_as_dataframe_files(vfile):
    """Read volume (CSV files) and return dataframe."""

    # "geogrid_vol.csv" --> "geogrid" etc
    gridname = vfile.replace("_vol.csv", "")

    fname = pathlib.Path(VFOLDER) / vfile

    dframe = pd.read_csv(fname)
    return dframe, gridname


def volume_as_dataframe_rms(vtable):
    """Read volume table in RMS and return dataframe."""

    # "geogrid_volumes" --> "geogrid" etc
    gridname = vtable.replace("_volumes", "")

    table = PRJ.volumetric_tables[vtable]
    dtdict = table.get_data_table().to_dict()

    dframe = pd.DataFrame.from_dict(dtdict)
    dframe.rename(columns=RENAMING, inplace=True)
    # skip REALIZATION
    dframe.drop("REALIZATION", axis=1, inplace=True)
    return dframe, gridname


def export_dataio(df, gridname):
    """Get the dataframe and export to SUMO via dataio."""

    exp = fmu.dataio.ExportData(
        name=gridname,
        config=CFG,
        content="volumetrics",
        unit="m",
        is_prediction=True,
        is_observation=False,
        tagname=TAGNAME,
        verbosity=VERBOSITY,
        workflow="Volume calculation",
    )

    out = exp.export(df)
    print(f"Exported volume table for {gridname} to {out}")


if __name__ == "__main__":

    if IN_ROXAR:
        for vtable in VTABLES:
            export_dataio(*volume_as_dataframe_rms(vtable))

    else:
        for vfile in VFILES:
            export_dataio(*volume_as_dataframe_files(vfile))
