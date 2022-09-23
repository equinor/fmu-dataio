"""Export unsmry"""

# In this example, the starting point is UNSMRY as a pyarrow.Table instance

import pathlib

import pyarrow as pa
import pyarrow.feather as feather

from fmu.config import utilities as ut
import fmu.dataio as dataio

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")


def export_unsmry(table):
    """Export a UNSMRY table"""

    ed = dataio.ExportData(
        name="MyUnsmry", config=CFG, content="unsmry", workflow="simulation"
    )

    out = ed.export(table)


def _read_unsmry(unsmry_path):
    """Read a UNSMRY table from disk."""

    # For the sake of the example, we get to a starting point where we have the UNSMRY
    # table as a pa.Table.

    return feather.read_table(unsmry_path)


if __name__ == "__main__":
    print("Export a UNSMRY table....", end="")
    table = _read_unsmry(pathlib.Path("../output/unsmry/UNSMRY.arrow"))
    export_unsmry(table)
    print("Done.")
