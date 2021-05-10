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

RUN = "tests/data/drogon/ertrun1/realization-0/iter-0/rms"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def test_instantate_class_no_keys():
    """Test function _get_meta_master."""
    # it should be possible to parse without any key options
    case = fmu.dataio.ExportData()
    for attr, value in case.__dict__.items():
        print(attr, value)

    assert case._verbosity == "CRITICAL"
    assert case._is_prediction is True


def test_get_meta_dollars():
    """The private routine that provides special <names> (earlier with $ in front)."""
    case = fmu.dataio.ExportData()
    case._config = CFG
    assert "schema" in case._meta_dollars["schema"]
    assert "fmu" in case._meta_dollars["source"]


def test_get_meta_masterdata():
    """The private routine that provides masterdata."""
    case = fmu.dataio.ExportData()
    case._config = CFG
    case._get_meta_masterdata()
    assert case._meta_masterdata["smda"]["country"][0]["identifier"] == "Norway"


def test_get_meta_access():
    """The private routine that provides access."""
    case = fmu.dataio.ExportData()
    case._config = CFG
    case._get_meta_access()
    assert case._meta_access["someaccess"] == "jail"


def test_get_meta_tracklog():
    """The private routine that provides tracklog."""
    # placeholder


def test_process_fmu_model():
    """The (second order) private routine that provides fmu:model"""
    case = fmu.dataio.ExportData()
    case._config = CFG
    fmumodel = case._process_meta_fmu_model()
    assert fmumodel["revision"] == "0.99.0"


def test_process_fmu_case():
    """The produce(!) the fmu case data."""

    case = fmu.dataio.ExportData()
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

    case = fmu.dataio.ExportData(verbosity="DEBUG", flag=1, config=CFG)
    case._pwd = pathlib.Path(RUN)

    case.case_metadata_to_file(
        casename="testcase",
        rootfolder=str(tmp_path),
        caseuser="ertuser",
        restart_from=None,
        description="My added description",
    )


def test_process_fmu_realisation():
    """The (second order) private routine that provides realization and iteration."""
    case = fmu.dataio.ExportData()
    case._config = CFG
    case._pwd = pathlib.Path(RUN)

    c_meta, i_meta, r_meta = case._process_meta_fmu_realization_iteration()
    logger.info("========== CASE")
    logger.info("%s", json.dumps(c_meta, indent=2, default=str))
    logger.info("========== ITER")
    logger.info("%s", json.dumps(i_meta, indent=2, default=str))
    logger.info("========== REAL")
    logger.info("%s", json.dumps(r_meta, indent=2, default=str))

    assert r_meta["parameters"]["THERYS_PORO_LS"] == 0.23
    assert i_meta["uid"] == "a40b05e8-e47f-47b1-8fee-f52a5116bd37--iter-0"
    assert c_meta["uuid"] == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"
