"""Test the main class DataExporter and functions in the dataio module."""
import json
import logging
import pathlib
from collections import OrderedDict

import yaml

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

    case = fmu.dataio.InitializeCase(runfolder=RUN)
    case._config = CFG

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

    case = fmu.dataio.InitializeCase(
        verbosity="DEBUG",
        config=CFG,
        runfolder=pathlib.Path(RUN),
    )

    case.export(
        casename="testcase",
        rootfolder=str(tmp_path),
        caseuser="ertuser",
        restart_from=None,
        description="My added description",
    )


def test_persisted_case_uuid(tmp_path):
    """
    Assert that the fmu.case.uuid is persisted when a case is
    initialized many times.

    Wanted behavior:

        When initializing a case for the first time, fmu.dataio
        should produce the case metadata.
        When initializing that case again, fmu.dataio should persist
        the fmu.case.uuid, so that subsequent data objects uploaded
        in two separate runs will inherit the same uuid.
    """

    case = fmu.dataio.InitializeCase(verbosity="DEBUG", config=CFG, runfolder=RUN)
    case.export(
        casename="testcase",
        rootfolder=str(tmp_path),
        caseuser="ertuser",
        restart_from=None,
        description="My added description",
    )

    case_metadata_filename = pathlib.Path(
        tmp_path / "share" / "metadata" / "fmu_case.yml"
    )

    with open(case_metadata_filename, "r") as stream:
        case_metadata = yaml.safe_load(stream)

    assert "fmu" in case_metadata
    assert "case" in case_metadata["fmu"]
    assert "uuid" in case_metadata["fmu"]["case"]

    first_uuid = case_metadata["fmu"]["case"]["uuid"]

    case.export(
        casename="testcase",
        rootfolder=str(tmp_path),
        caseuser="ertuser",
        restart_from=None,
        description="My added description",
    )

    case_metadata_filename = pathlib.Path(
        tmp_path / "share" / "metadata" / "fmu_case.yml"
    )

    with open(case_metadata_filename, "r") as stream:
        case_metadata = yaml.safe_load(stream)

    second_uuid = case_metadata["fmu"]["case"]["uuid"]

    assert first_uuid == second_uuid
