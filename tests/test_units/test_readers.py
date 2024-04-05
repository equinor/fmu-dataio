"""Test the readers module"""

import pytest
from fmu.dataio import readers


def test_faultroomsurface_reader(rootpath):
    """Test reading the special in-house faultroom surface."""

    relpath = "tests/data/drogon/rms/output/faultroom/ex_faultroom_1.3.1.json"
    faultroom_file = rootpath / relpath

    instance = readers.read_faultroom_file(faultroom_file)

    assert instance.faults == ["F1", "F2", "F3", "F4", "F5", "F6"]
    assert instance.juxtaposition_fw == ["Therys", "Valysar", "Volon"]
    assert instance.juxtaposition_hw == ["Therys", "Valysar", "Volon"]
    assert instance.properties == [
        "Juxtaposition",
        "displacement_avg",
        "permeability_avg",
        "transmissibility_avg",
    ]
    assert instance.bbox["xmin"] == pytest.approx(459495.34)
    assert instance.bbox["xmax"] == pytest.approx(465799.178)
    assert instance.bbox["ymin"] == pytest.approx(5930019.302)
    assert instance.bbox["ymax"] == pytest.approx(5937680.563)
    assert instance.bbox["zmin"] == pytest.approx(1556.379)
    assert instance.bbox["zmax"] == pytest.approx(1831.14)

    assert instance.name == "TopVolantis"
    assert instance.tagname[:9] == "faultroom"
