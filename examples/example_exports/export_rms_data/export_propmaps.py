"""Export maps that holds certain average gridmodel properties.

The files on disk are:

facies_fraction_channels_volon.gri
klogh_average_valysar.gri
phit_average_therys.gri

We want to use the file names here to extract some data (like name of formation, e.g.
Therys).
"""

from pathlib import Path

import xtgeo
from fmu.config import utilities as ut

from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

# Property attributes. This maps a property name (key) to an attribute name (value).
PROP_ATTRIBUTE_MAP = {
    "facies_fraction": "facies_fraction",
    "phit": "porosity",
    "klog": "permeability",
}

# Name attributes. This maps a name in the map (key) to a name used for export (value).
NAME_MAP = {
    "valysar": "Valysar",
    "therys": "Therys",
    "volon": "Volon",
}

MAPS_DIR = Path("../output/maps/grid_averages")


def export_property_maps():
    """Re-export maps with metadata."""

    map_files = MAPS_DIR.glob("*.gri")
    for file in map_files:
        surf = xtgeo.surface_from_file(file)

        attribute = "unset"
        for from_prop, to_attribute in PROP_ATTRIBUTE_MAP.items():
            if from_prop in str(file).lower():
                attribute = to_attribute

        name = "unset"
        for from_name, to_name in NAME_MAP.items():
            if from_name in str(file).lower():
                name = to_name

        export_data = ExportData(
            config=CFG,
            name=name,
            unit="fraction",
            content="property",
            content_metadata={"attribute": attribute, "is_discrete": False},
            tagname=f"average_{attribute}",
            workflow="rms property model",
        )

        out_path = export_data.export(surf)
        print(f"Exported property map to file {out_path}")


def main():
    print("\nExporting property maps and metadata...")
    export_property_maps()
    print("Done exporting property maps and metadata.")


if __name__ == "__main__":
    main()
