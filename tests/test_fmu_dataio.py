from collections import OrderedDict

import fmu.dataio

CFG = OrderedDict()
CFG["template"] = {"name": "Test", "revision": "AUTO"}
CFG["masterdata"] = {
    "smda": {
        "country": [
            {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
        ],
        "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
    }
}


def test_instantate_class():
    """Test function _get_meta_master."""
    case = fmu.dataio.ExportData(config=CFG)
    assert isinstance(case._config, dict)
