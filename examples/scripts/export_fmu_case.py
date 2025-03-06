import logging

from fmu.config import utilities as utils
from fmu.dataio.case import CreateCaseMetadata

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CFG = utils.yaml_load("fmuconfig/output/global_variables.yml")


def create_case():
    case = CreateCaseMetadata(
        config=CFG,
        rootfolder="",
        casename="MyCase",
        caseuser="Test",
    )
    fname = case.export()
    print(f"Exported case metadata to file {fname}")


if __name__ == "__main__":
    print("\nCreate and export new fmu case metadata...")
    create_case()
    print("Done creating new fmu case metadata.")
