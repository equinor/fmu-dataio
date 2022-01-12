"""Export faultpolygons via dataio with metadata."""
from pathlib import Path

import xtgeo
from fmu.config import utilities as utils

import fmu.dataio as dataio

CFG = utils.yaml_load("../../fmuconfig/output/global_variables.yml")

HORISONNAMES = CFG["rms"]["horizons"]["TOP_RES"]

# if inside RMS
RMS_POL_CATEGORY = "GL_faultlines_extract_postprocess"

# if running outside RMS using files that are stored e.g. on rms/output
FILEROOT = Path("../output/polygons")


def export_faultlines():
    """Return faultlines as both dataframe and original (xyz)"""

    ed = dataio.ExportData(
        config=CFG,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="faultlines",
        verbosity="INFO",
        workflow="rms structural model",
    )

    for hname in HORISONNAMES:

        # RMS version for reading polygons from a project:
        # poly = xtgeo.polygons_from_roxar(project, hname, RMS_POL_CATEGORY)

        # File version:
        poly = xtgeo.polygons_from_file((FILEROOT / hname.lower()).with_suffix(".pol"))

        poly.name = hname

        # Export both csv (keeping xtgeo column names) and irap text format
        # The difference bewtween "csv" and "csv|xtgeo" is that the latter will keep
        # xtgeo column names as-is while "csv" will force column names to "X Y Z ID"
        for fmt in ["csv|xtgeo", "irap_ascii"]:
            ed.polygons_fformat = fmt
            ed.export(poly, verbosity="WARNING")


if __name__ == "__main__":
    export_faultlines()
