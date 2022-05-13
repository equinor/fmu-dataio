"""Export maps that holds certain average gridmodel properties.

The files on disk are:

facies_fraction_channels_volon.gri
klogh_average_valysar.gri
phit_average_therys.gri

We wan to use the file names here to extract some data (like name of formation,
e.g. Therys).

"""
from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

import fmu.dataio as dataio

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

dataio.ExportData._inside_rms = True


def main():
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
            content={"property": {"attribute": attribute, "is_discrete": False}},
            vertical_domain={"depth": "msl"},
            timedata=None,
            is_prediction=True,
            is_observation=False,
            tagname="average_" + attribute,
            verbosity="INFO",
            workflow="rms property model",
        )
        fname = ed.export(surf)
        print(f"File name is {fname}")


if __name__ == "__main__":
    main()
    print("That's all")
