"""Test the main class DataExporter and functions in the dataio module."""
import pathlib
from collections import OrderedDict
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


def test_process_fmu_ensemble():
    """The (second order) private routine that provides fmu:realization and ensemble."""
    # this is a more tricky one as it used the folder structure and jobs.json
    # and parameters.json from ERT
    case = fmu.dataio.ExportData()
    case._config = CFG
    case._pwd = pathlib.Path(RUN)

    r_meta, e_meta = case._process_meta_fmu_realization_ensemble()
    print(json.dumps(r_meta, indent=2, default=str))
    print(json.dumps(e_meta, indent=2, default=str))

    assert r_meta["parameters"]["THERYS_PORO_LS"] == 0.23
    assert e_meta["id"] == "26295_22197_2021-4-20-12-50-55_406759315d"
