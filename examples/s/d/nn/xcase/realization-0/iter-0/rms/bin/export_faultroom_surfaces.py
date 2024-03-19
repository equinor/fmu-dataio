"""Export faultroom surfaces via dataio with metadata."""

import logging
from pathlib import Path

import fmu.dataio as dataio
from fmu.config import utilities as utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = utils.yaml_load("../../fmuconfig/output/global_variables.yml")

# if running outside RMS using files that are stored e.g. on rms/output
FAULTROOM_FILE = Path("../output/faultroom/some_faultroom.json")


def export_faultroom_surface():
    """Export faultroom data, json files made by FaultRoom plugin in RMS"""

    # read file and return a FaultRoomSurface instance
    faultroom_object = dataio.readers.read_faultroom_file(FAULTROOM_FILE)

    ed = dataio.ExportData(
        config=CFG,
        content="fault_properties",
        unit="unset",
        vertical_domain={"depth": "msl"},
        is_prediction=True,
        is_observation=False,
        workflow="rms structural model",
        tagname=faultroom_object.tagname,
    )

    ed.export(faultroom_object)


if __name__ == "__main__":
    export_faultroom_surface()
