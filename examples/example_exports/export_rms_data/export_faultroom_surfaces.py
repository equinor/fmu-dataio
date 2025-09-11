"""Export faultroom surfaces via dataio with metadata."""

import logging
from pathlib import Path

from fmu.config import utilities as utils

from fmu import dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = utils.yaml_load("../../fmuconfig/output/global_variables.yml")

# if running outside RMS using files that are stored e.g. on rms/output
FAULTROOM_FILE = Path("../output/faultroom/some_faultroom.json")


def export_faultroom_surfaces():
    """Export faultroom data, json files made by FaultRoom plugin in RMS"""

    # read file and return a FaultRoomSurface instance
    faultroom_object = dataio._readers.faultroom.read_faultroom_file(FAULTROOM_FILE)

    ed = dataio.ExportData(
        config=CFG,
        content="fault_properties",
        unit="unset",
        vertical_domain="depth",
        domain_reference="msl",
        is_prediction=True,
        is_observation=False,
        workflow="rms structural model",
        tagname=faultroom_object.tagname,
    )

    fname = ed.export(faultroom_object)
    print(f"Exported to file {fname}")


def main():
    print("\nExporting faultroom surface maps and metadata...")
    export_faultroom_surfaces()
    print("Done exporting faultroom surface maps and metadta.")


if __name__ == "__main__":
    main()
