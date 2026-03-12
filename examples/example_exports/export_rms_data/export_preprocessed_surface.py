"""Export a preprocessed surface with metadata."""

from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu.dataio.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

DEPTH_FILE = Path("../output/maps/structure/") / "topvolantis--ds_extract_geogrid.gri"


def export_preprocessed_surface():
    """Export a preprocessed surface with metadata."""

    export_data = ExportData(
        config=CFG,
        preprocessed=True,
        name="preprocessedmap",
        fmu_context="case",
        content="depth",
        is_observation=True,
        subfolder="mysub",
    )

    surf_depth = xtgeo.surface_from_file(DEPTH_FILE)
    export_data.export(surf_depth)
    print("Exported a preprocessed depth surface.")


def main():
    print("\nExporting a preprocessed surface and metadata...")
    export_preprocessed_surface()
    print("Done exporting a preprocessed surface and metadata.")


if __name__ == "__main__":
    main()
