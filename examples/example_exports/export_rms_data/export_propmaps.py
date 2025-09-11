"""Export maps that holds certain average gridmodel properties.

The files on disk are:

facies_fraction_channels_volon.gri
klogh_average_valysar.gri
phit_average_therys.gri

We wan to use the file names here to extract some data (like name of formation,
e.g. Therys).

"""

import logging
from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu import dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

# property attributes, the key is "pattern" and the value is generic name to be used:
TRANSLATE = {
    "facies_fraction": "facies_fraction",
    "phit": "porosity",
    "klog": "permeability",
}

# name attributes, the key is "pattern" and the value is name to be used:
NAMETRANSLATE = {
    "valysar": "Valysar",
    "therys": "Therys",
    "volon": "Volon",
}

INPUT_FOLDER = Path("../output/maps/grid_averages")


def export_propmaps():
    """Exporting maps from clipboard"""

    files = INPUT_FOLDER.glob("*.gri")
    for file in files:
        surf = xtgeo.surface_from_file(file)

        attribute = "unset"
        for pattern, attr in TRANSLATE.items():
            if pattern in str(file).lower():
                attribute = attr

        name = "unset"
        for pattern, attr in NAMETRANSLATE.items():
            if pattern in str(file).lower():
                name = attr

        ed = dataio.ExportData(
            config=CFG,
            name=name,
            unit="fraction",
            content="property",
            content_metadata={"attribute": attribute, "is_discrete": False},
            vertical_domain="depth",
            domain_reference="msl",
            timedata=None,
            is_prediction=True,
            is_observation=False,
            tagname="average_" + attribute,
            workflow="rms property model",
        )

        fname = ed.export(surf)
        print(f"Exported property map to file {fname}")


def main():
    print("\nExporting property maps and metadata...")
    export_propmaps()
    print("Done exporting property maps and metadata.")


if __name__ == "__main__":
    main()
