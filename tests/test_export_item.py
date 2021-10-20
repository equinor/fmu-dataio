"""Test the individual functions in module _export_item."""
import json
from collections import OrderedDict

import pytest
import xtgeo
import yaml

import fmu.dataio
import fmu.dataio._export_item as ei

# pylint: disable=no-member

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
        verbosity="INFO",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_name()
    assert dataio.metadata4data["name"] == "Valysar Fm."

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
    assert dataio.metadata4data["name"] == "Valysar Fm."

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
    assert dataio.metadata4data["name"] == "Something else"
    assert "stratigraphic" in dataio.metadata4data
    assert dataio.metadata4data["stratigraphic"] is False


def test_data_process_context():
    """Test the _data_process_context function."""
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
        context=rel1,
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(ncol=3, nrow=4, xinc=22, yinc=22, values=0)

    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")

    exportitem._data_process_context()
    assert dataio.metadata4data["offset"] == 4.0
    assert dataio.metadata4data["top"]["name"] == "VOLANTIS GP. Top"
    assert dataio.metadata4data["base"]["stratigraphic"] is True

    # test rel2
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        context=rel2,
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(ncol=3, nrow=4, xinc=22, yinc=22, values=0)

    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")

    with pytest.raises(ValueError) as verr:
        exportitem._data_process_context()
    assert "Cannot find Volon FM. Top" in str(verr)

    # test rel3
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        context=rel3,
        config=CFG2,
        content="depth",
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(ncol=3, nrow=4, xinc=22, yinc=22, values=0)

    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")

    # with pytest.warns(UserWarning) as uwarn:
    #     exportitem._data_process_context()
    # assert "context top and/base is present but" in str(uwarn)


def test_data_process_timedata():
    """Test the _data_process_timedata function."""
    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content="depth",
        timedata=[["20230101", "monitor"], [20210902, "base"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_timedata()
    print(json.dumps(dataio.metadata4data["time"], indent=2, default=str))
    assert dataio.metadata4data["time"][0]["value"] == "2023-01-01T00:00:00"
    assert dataio.metadata4data["time"][0]["label"] == "monitor"


def test_data_process_content():
    """Test the _data_process_content function."""
    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content="depth",
        timedata=[["20230101", "monitor"], [20210902, "base"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_content()
    assert dataio.metadata4data["content"] == "depth"

    # test case 2
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"seismic": {"attribute": "attribute_timeshifted_somehow"}},
        timedata=[["20230101", "monitor"], [20210902, "base"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_content()
    assert dataio.metadata4data["content"] == "seismic"
    assert (
        dataio.metadata4data["seismic"]["attribute"] == "attribute_timeshifted_somehow"
    )


def test_data_process_content_shall_fail():
    """Test the _data_process_content function for invalid entries."""
    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content="something_invalid",
        timedata=[["20230101", "monitor"], [20210902, "base"]],
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
        timedata=[["20230101", "monitor"], [20210902, "base"]],
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
        timedata=[["20230101", "monitor"], [20210902, "base"]],
        tagname="WhatEver",
    )
    obj = xtgeo.RegularSurface(
        name="SomeName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    with pytest.raises(ei.ValidationError) as errmsg:
        exportitem._data_process_content()
    assert "is not valid for" in str(errmsg)


def test_data_process_content_validate():
    """Test the content validation"""

    # test case 1 - fluid contact, valid
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"fluid_contact": {"contact": "owc"}},
    )
    obj = xtgeo.Polygons()
    exportitem = ei._ExportItem(dataio, obj, verbosity="INFO")
    exportitem._data_process_content()

    assert "fluid_contact" in dataio.metadata4data

    # test case 2 - fluid contact, not valid, shall fail
    dataio = fmu.dataio.ExportData(
        name="SomeName",
        config=CFG2,
        content="fluid_contact",
    )
    obj = xtgeo.Polygons()
    exportitem = ei._ExportItem(dataio, obj, verbosity="DEBUG")
    with pytest.raises(ei.ValidationError):
        exportitem._data_process_content()


def test_data_process_content_fluid_contact():
    """Test the field fluid_contact."""

    # test case 1
    dataio = fmu.dataio.ExportData(
        name="Valysar",
        config=CFG2,
        content={"fluid_contact": {"contact": "owc"}},
        timedata=[["20230101", "monitor"], [20210902, "base"]],
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
        timedata=[["20210101", "monitor"], [20210902, "base"]],
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
        timedata=[["20230101", "monitor"], [20210902, "base"]],
        tagname="WhatEver",
    )
    obj = xtgeo.Polygons()


def test_display():
    """
    Test the display.

    For now, the display.name only is set. It is set by
    input argument, with two fallbacks.

    1) input argument to ExportData.export()
    2) Fallback: name argument to Export Data initialisation
    3) Fallback: Object name

    Note: Will not use object name if this is == "unknown",
    which is the default in XTgeo.

    """

    # 1 assert that name argument is used when set
    dataio = fmu.dataio.ExportData(
        name="MyName", config=CFG2, content="depth", verbosity="DEBUG"
    )

    obj = xtgeo.RegularSurface(
        name="ObjectName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exporter = ei._ExportItem(dataio, obj, verbosity="DEBUG")
    exporter._display()

    # 'display_name' is not given, so 'name' should be used.
    assert dataio.metadata4display["name"] == "MyName"

    # 2 assert that object argument is used when name argument not set
    dataio = fmu.dataio.ExportData(
        config=CFG2,
        content="depth",
        verbosity="DEBUG",
    )

    obj = xtgeo.RegularSurface(
        name="ObjectName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exporter = ei._ExportItem(dataio, obj, verbosity="DEBUG")
    exporter._display()

    # 'display_name' nor 'name' is given, object name should be used
    assert dataio.metadata4display["name"] == "ObjectName"

    # 3 assert that None is set when nothing is given
    dataio = fmu.dataio.ExportData(
        config=CFG2,
        content="depth",
        verbosity="DEBUG",
    )

    obj = xtgeo.RegularSurface(ncol=3, nrow=4, xinc=22, yinc=22, values=0)
    exporter = ei._ExportItem(dataio, obj, verbosity="DEBUG")
    exporter._display()

    # None of the fallbacks are set, so None should be exported
    assert dataio.metadata4display["name"] is None

    # 4 assert that display_name is used when given
    dataio = fmu.dataio.ExportData(
        name="MyName",
        display_name="MyDisplayName",
        config=CFG2,
        content="depth",
        verbosity="DEBUG",
    )

    obj = xtgeo.RegularSurface(
        name="ObjectName", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )
    exporter = ei._ExportItem(dataio, obj, verbosity="DEBUG")
    exporter._display()
    assert dataio.metadata4display["name"] == "MyDisplayName"
