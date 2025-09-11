"""Create case metadata using fmu-dataio."""

import logging

from fmu.config import utilities as utils

from fmu.dataio.case import CreateCaseMetadata

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = utils.yaml_load("fmuconfig/output/global_variables.yml")


def create_case_metadata():
    """Create case metadata"""

    case = CreateCaseMetadata(
        config=CFG,
        rootfolder="",
        casename="MyCase",
    )

    fname = case.export()
    print(f"Exported case metadata to file {fname}")


def main():
    print("\nCreate and export a new fmu case metadata...")
    create_case_metadata()
    print("Done creating a new fmu case metadata.")


if __name__ == "__main__":
    main()
