"""Test the main class DataExporter and functions in the dataio module."""
import pathlib
from collections import OrderedDict
import logging
import json
import fmu.dataio

CFG = OrderedDict()
CFG["model"] = {"name": "Test", "revision": "21.0.0"}
CFG["masterdata"] = {
    "smda": {
        "country": [
            {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
        ],
        "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
    }
}
CFG["stratigraphy"] = {"TopVolantis": {}}
CFG["access"] = {"someaccess": "jail"}
CFG["model"] = {"revision": "0.99.0"}
CFG["access"] = {"asset": "Drogon", "ssdl": "internal"}

RUN = "tests/data/drogon/ertrun1/realization-0/iter-0/rms"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def test_process_fmu_case():
    """The produce(!) the fmu case data."""

    case = fmu.dataio.InitializeCase()
    case._config = CFG
    case._pwd = pathlib.Path(RUN)

    c_meta = case._establish_fmu_case_metadata(
        casename="testcase",
        caseuser="ertuser",
        restart_from=None,
        description="My added description",
    )

    print(json.dumps(c_meta, indent=2))
    assert c_meta["user"]["id"] == "ertuser"


def test_fmu_case_meta_to_file(tmp_path):
    """The produce(!) the fmu case data on disk."""

    case = fmu.dataio.InitializeCase(verbosity="DEBUG", config=CFG)
    case._pwd = pathlib.Path(RUN)

    case.to_file(
        casename="testcase",
        rootfolder=str(tmp_path),
        caseuser="ertuser",
        restart_from=None,
        description="My added description",
    )
