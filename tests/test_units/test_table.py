"""Tests for table index
"""
from pathlib import Path
import pandas as pd
import shutil
import pytest
import logging
from fmu.dataio import ExportData
from fmu.config.utilities import yaml_load

# @pytest.fixture(name="globalconfig2")
# def fixture_config():
# """Gets global variables dict

# Returns:
# dict: the global var dict
# """
# config_path = "tests/data/drogon/global_config2/global_variables.yml"
# return yaml_load(config_path)


logging.basicConfig(level="ERROR")


@pytest.fixture(name="sum_data")
def fixture_sum_data():
    """Return summary mock data

    Returns:
        pd.DataFram: dummy data
    """
    return pd.DataFrame({"alf": ["A", "B", "C"], "DATE": [1, 2, 3]})


@pytest.fixture(name="vol_data")
def fixture_vol_data():
    """Return volume mock data

    Returns:
        pd.DataFrame: dummy data
    """
    return pd.DataFrame(
        {
            "ZONE": ["A", "B", "C"],
            "LICENCE": ["L1", "L2", "L2"],
            "nums": [1, 2, 3],
            "OTHER": ["c", "d", "f"],
        }
    )


def assert_works(file_path, answer):
    """does the assert work for all tests

    Args:
        file_path (string): path to generated file
        answer (list): expected answer
    """
    file_path = Path(file_path)
    meta = yaml_load(file_path.parent / f".{file_path.name}.yml")
    index = meta["data"]["table_index"]
    fail_string = f"table index should be {answer}, but is {index}"
    assert meta["data"]["table_index"] == answer, fail_string


def test_inplace_volume_index(vol_data, globalconfig2):
    """Test volumetric data

    Args:
        vol_data (pd.DataFrame): a volumetriclike dataset
        globalconfig2 (dict): one global variables dict
    """
    answer = ["ZONE", "LICENCE"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(vol_data, name="baretull")
    assert_works(path, answer)


def test_summary_index(sum_data, globalconfig2):
    """Test summary data

    Args:
        sum_data (pd.DataFrame): summary "like" dataframe
        globalconfig2 (dict): global variables dict
    """
    answer = ["DATE"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(sum_data, name="baretull")
    assert_works(path, answer)


def test_set_from_exportdata(vol_data, globalconfig2):
    """Test setting of index from class ExportData

    Args:
        vol_data (pd.DataFrame): a volumetric like dataframe
        globalconfig2 (dict): one global variables dict
    """
    index = ["OTHER"]
    exd = ExportData(config=globalconfig2, table_index=index)
    path = exd.export(vol_data, name="baretull")
    assert_works(path, index)


def test_set_from_export(vol_data, globalconfig2):
    """Test setting of index from method export on class ExportData

    Args:
        vol_data (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variable dict
    """
    index = ["OTHER"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(vol_data, name="baretull", table_index=index)
    assert_works(path, index)


def test_set_table_index_not_in_table(vol_data, globalconfig2):
    """Test when setting index with something that is not in data

    Args:
        vol_data (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variables dict
    """
    index = ["banana"]
    exd = ExportData(config=globalconfig2)
    with pytest.raises(KeyError) as k_err:
        exd.export(vol_data, name="baretull", table_index=index)
