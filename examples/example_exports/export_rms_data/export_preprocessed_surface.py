"""Export a preprocessed surface with metadata."""

from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu.dataio.dataio import ExportData

SCRIPT_DIR = Path(__file__).resolve().parent
EXAMPLES_ROOT = SCRIPT_DIR.parents[1]

CFG = ut.yaml_load(EXAMPLES_ROOT / "fmuconfig/output/global_variables.yml")

DEPTH_FILE = (
    SCRIPT_DIR.parent / "output/maps/structure/topvolantis--ds_extract_geogrid.gri"
)


def export_preprocessed_surface():
    """Export a preprocessed surface with metadata."""
    export_data = ExportData(
        config=CFG,
        preprocessed=True,
        name="preprocessedmap",
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
