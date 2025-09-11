"""Export polygons via dataio with metadata."""

import logging
from pathlib import Path

import xtgeo
from fmu.config import utilities as utils

from fmu import dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = utils.yaml_load("../../fmuconfig/output/global_variables.yml")

# if running outside RMS using files that are stored e.g. on rms/output
FILEROOT = Path("../output/polygons")


def export_field_region():
    """Export metadata for a field region"""

    ed = dataio.ExportData(
        config=CFG,
        content="field_region",
        content_metadata={"id": 1},
        unit="m",
        vertical_domain="depth",
        domain_reference="msl",
        timedata=None,
        is_prediction=False,
        is_observation=False,
        tagname="polygons_field_region",
        workflow="rms structural model",
    )

    horizon = "BaseVolantis"
    polygon = xtgeo.polygons_from_file((FILEROOT / horizon.lower()).with_suffix(".pol"))
    polygon.name = horizon
    ed.polygons_fformat = "csv|xtgeo"

    ed.export(polygon)
    print("Exported field region for " + horizon)


def export_field_outline():
    """Export metadata for a field outline"""
    ed = dataio.ExportData(
        config=CFG,
        content="field_outline",
        content_metadata={"contact": "goc"},
        unit="m",
        vertical_domain="depth",
        domain_reference="msl",
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="polygons_field_outline",
        workflow="rms structural model",
    )

    horizon = "BaseVolantis"
    polygon = xtgeo.polygons_from_file((FILEROOT / horizon.lower()).with_suffix(".pol"))
    polygon.name = horizon
    ed.polygons_fformat = "csv|xtgeo"

    ed.export(polygon)
    print("Exported field outline for " + horizon)


def main():
    print("\nExporting polygons and metadata...")
    export_field_region()
    export_field_outline()
    print("Done exporting polygons and metadata.")


if __name__ == "__main__":
    main()
