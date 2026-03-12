"""Export FaultRoom surfaces from RMS."""

from pathlib import Path

from fmu.config import utilities as ut

from fmu.dataio import ExportData
from fmu.dataio._readers import faultroom

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

# If running outside RMS using files that are stored e.g. on rms/output
FAULTROOM_FILE = Path("../output/faultroom/some_faultroom.json")


def export_faultroom_surface():
    """Export FaultRoom surace.

    FaultRoom data are json files created by the FaultRoom plugin in RMS."""

    # Read file and return a FaultRoomSurface instance
    faultroom_object = faultroom.read_faultroom_file(FAULTROOM_FILE)

    export_data = ExportData(
        config=CFG,
        content="fault_properties",
        workflow="rms structural model",
        tagname=faultroom_object.tagname,
    )

    out_path = export_data.export(faultroom_object)
    print(f"Exported to file {out_path}")


def main():
    print("\nExporting faultroom surface maps and metadata...")
    export_faultroom_surface()
    print("Done exporting faultroom surface maps and metadta.")


if __name__ == "__main__":
    main()
