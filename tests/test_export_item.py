"""Test the individual functions in module _export_item."""
from collections import OrderedDict
import xtgeo
import json
import yaml
import pytest

import fmu.dataio
import fmu.dataio._export_item as ei


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

CFG2 = {}
with open("tests/data/drogon/global_config2/global_variables.yml", "r") as stream:
    CFG2 = yaml.safe_load(stream)


def test_data_process_name():
    """Test the _data_process_name function."""
    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_name()
    assert dataio._meta_data["name"] == "Valysar Fm."

    # test case 2, name is given via object
    dataio = fmu.dataio.ExportData(
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="Valysar", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_name()
    assert dataio._meta_data["name"] == "Valysar Fm."

    # test case 3, name is given via object but not present in stratigraphy
    dataio = fmu.dataio.ExportData(
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="Something else", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_name()
    assert dataio._meta_data["name"] == "Something else"
    assert "stratigraphic" in dataio._meta_data
    assert dataio._meta_data["stratigraphic"] is False


def test_data_process_relation():
    """Test the _data_process_relation function."""
    # 1: name is given by RMS name:
    rel1 = {
        "offset": 4.0,
        "top": {"ref": "TopVolantis", "offset": 2.0},
        "base": {"ref": "TopVolon", "offset": 0.0},
    }
    # 2: name is given as mix of SMDA name and RMS name:
    rel2 = {
        "offset": 4.0,
        "top": {"ref": "TopVolantis", "offset": 2.0},
        "base": {"ref": "Volon FM. Top", "offset": 0.0},
    }
    # 3: ref is missing for top
    rel3 = {
        "offset": 4.0,
        "top": {"offset": 2.0},
        "base": {"ref": "Volon FM. Top", "offset": 0.0},
    }

    # test rel1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        relation=rel1,
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(ncol=3, nrow=4, xinc=22, yinc=22, values=0)

    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")

    exportitem._data_process_relation()
    assert dataio._meta_data["offset"] == 4.0
    assert dataio._meta_data["top"]["name"] == "VOLANTIS GP. Top"
    assert dataio._meta_data["base"]["stratigraphic"] is True

    # test rel2
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        relation=rel2,
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(ncol=3, nrow=4, xinc=22, yinc=22, values=0)

    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")

    with pytest.raises(ValueError) as verr:
        exportitem._data_process_relation()
    assert "Cannot find Volon FM. Top" in str(verr)

    # test rel3
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        relation=rel3,
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(ncol=3, nrow=4, xinc=22, yinc=22, values=0)

    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")

    # with pytest.warns(UserWarning) as uwarn:
    #     exportitem._data_process_relation()
    # assert "Relation top and/base is present but" in str(uwarn)


def test_data_process_timedata():
    """Test the _data_process_timedata function."""
    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content="depth",
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_timedata()
    print(json.dumps(dataio._meta_data["time"], indent=2, default=str))
    assert dataio._meta_data["time"][0]["value"] == "2021-01-01T00:00:00"
    assert dataio._meta_data["time"][0]["label"] == "first"


def test_data_process_content():
    """Test the _data_process_content function."""
    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content="depth",
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_content()
    assert dataio._meta_data["content"] == "depth"

    # test case 2
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"seismic": {"attribute": "attribute_timeshifted_somehow"}},
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_content()
    assert dataio._meta_data["content"] == "seismic"
    assert dataio._meta_data["seismic"]["attribute"] == "attribute_timeshifted_somehow"


def test_data_process_content_shall_fail():
    """Test the _data_process_content function for invalid entries."""
    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content="something_invalid",
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    with pytest.raises(ei.ValidationError) as errmsg:
        exportitem._data_process_content()
    assert "Invalid content" in str(errmsg)

    # test case 2, valid key but invalid value
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"seismic": {"attribute": 100}},
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    with pytest.raises(ei.ValidationError) as errmsg:
        exportitem._data_process_content()
    assert "Invalid type" in str(errmsg)

    # test case 3, valid content key but invalid attribute key
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"seismic": {"invalid_attribute": "some"}},
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    with pytest.raises(ei.ValidationError) as errmsg:
        exportitem._data_process_content()
    assert "is not valid for" in str(errmsg)


def test_data_process_content_fluid_contact():
    """Test the field fluid_contact."""
    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"fluid_contact": {"contact": "owc"}},
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.Polygons()
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_content()

    # test case 2
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"fluid_contact": {"wrong": "owc"}},
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.Polygons()
    with pytest.raises(ei.ValidationError) as errmsg:
        exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
        exportitem._data_process_content()
    assert "is not valid for" in str(errmsg)

    # test case 3
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"field_outline": {"wrong": "owc"}},
        timedata=[["20210101", "first"], [20210902, "second"]],
        tagname="WhatEver",
    )
    obj = xtgeo.Polygons()
