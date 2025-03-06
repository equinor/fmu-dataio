import logging
from pathlib import Path

from fmu.config import utilities as utils
import xtgeo

from fmu.dataio.dataio import ExportData

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = utils.yaml_load("../fmuconfig/output/global_variables.yml")

FILES = {
    "depth": Path("../output/maps/structure/") / "topvolantis--ds_extract_geogrid.gri",
}


def export_preprocessed_surface():

    edata = ExportData(
        config=CFG,  # read from global config
        preprocessed=True,
        name="preprocessedmap",
        fmu_context="case",
        content="depth",
        is_observation=True,
        subfolder="mysub",
    )
    surf_depth = xtgeo.surface_from_file(FILES["depth"])
    
    edata.export(surf_depth)
    print("Exported preprocessed depth surface.")


if __name__ == "__main__":
    print("\nExporting a preprocessed surface and metadata...")
    export_preprocessed_surface()
    print("Done exporting a preprocessed surface and metadata.")