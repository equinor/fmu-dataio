import pytest
from pathlib import Path
import numpy as np
from xtgeo import GridProperty
from fmu.dataio import ExportData
from fmu.config.utilities import yaml_load


def test_export_gridproperty_export(gridproperty, globalconfig2):
    """Test export of grid property with parent

    Args:
        gridproperty (xtgeo.GridProperty): property to export
        globalconfig2 (dict): dict containing the metadata
    """
    exd = ExportData(config=globalconfig2)
    path = exd.export(gridproperty, name=gridproperty.name, parent="MyGrid")
    posix_path = Path(path)
    meta = yaml_load(posix_path.parent / f".{posix_path.name}.yml")
    assert (
        meta["data"]["content"] == "grid_property"
    ), "Grid property not assigned correct content, content is meta['data']['content']"
    assert (
        "parent" in meta["data"]["grid_property"]
    ), "Grid property not assigned a parent"
    assert (
        meta["data"]["grid_property"]["parent"] == "MyGrid"
    ), f"Wrong parent name, should be MyGrid is {meta['data']['grid_property']['parent']}"
