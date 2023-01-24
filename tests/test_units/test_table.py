"""Tests for table index
"""
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pytest
from fmu.dataio import ExportData
from fmu.config.utilities import yaml_load
from fmu.dataio._objectdata_provider import _ObjectDataProvider


@pytest.fixture(name="edataobj3")
def fixture_edataobj1(globalconfig1):
    """Combined globalconfig and settings to instance, for internal testing"""
    # logger.info("Establish edataobj1")

    eobj = ExportData(
        config=globalconfig1, name="summary", content="timeseries", tagname=""
    )

    return eobj


@pytest.fixture(name="mock_sum_data")
def fixture_sum_data():
    """Return summary mock data

    Returns:
        pd.DataFram: dummy data
    """
    return pd.DataFrame({"alf": ["A", "B", "C"], "DATE": [1, 2, 3]})


@pytest.fixture(name="drogon_sum_data")
def fixture_drogon_sum():
    """Return pyarrow table

    Returns:
        pa.Table: table with summary data
    """
    path = "~/git/fmu-dataio-dbs/tests/data/drogon/tabular/summary.arrow"
    table = pa.feather.read_table(path)
    return table


@pytest.fixture(name="mock_vol_data")
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
    meta_path = file_path.parent / f".{file_path.name}.yml"
    meta = yaml_load(meta_path)
    file_path.unlink()
    meta_path.unlink()
    index = meta["data"]["table_index"]
    type_failure = f"{index} should be list, but is {type(index)}"
    fail_string = f"table index should be {answer}, but is {index}"
    assert isinstance(index, list), type_failure
    assert index == answer, fail_string


def test_inplace_volume_index(mock_vol_data, globalconfig2):
    """Test volumetric data

    Args:
        mock_vol_data (pd.DataFrame): a volumetriclike dataset
        globalconfig2 (dict): one global variables dict
    """
    answer = ["ZONE", "LICENCE"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(mock_vol_data, name="baretull")
    assert_works(path, answer)


def test_derive_summary_index_pandas(mock_sum_data, globalconfig2):
    """Test summary data

    Args:
        mock_sum_data (pd.DataFrame): summary "like" dataframe
        globalconfig2 (dict): global variables dict
    """
    answer = ["DATE"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(mock_sum_data, name="baretull")
    assert_works(path, answer)


def test_derive_summary_index_pyarrow(mock_sum_data, globalconfig2):
    """Test summary data

    Args:
        mock_sum_data (pd.DataFrame): summary "like" dataframe
        globalconfig2 (dict): global variables dict
    """
    answer = ["DATE"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(pa.Table.from_pandas(mock_sum_data), name="baretull")
    assert_works(path, answer)


def test_set_from_exportdata(mock_vol_data, globalconfig2):
    """Test setting of index from class ExportData

    Args:
        mock_vol_data (pd.DataFrame): a volumetric like dataframe
        globalconfig2 (dict): one global variables dict
    """
    index = ["OTHER"]
    exd = ExportData(config=globalconfig2, table_index=index)
    path = exd.export(mock_vol_data, name="baretull")
    assert_works(path, index)


def test_set_from_export(mock_vol_data, globalconfig2):
    """Test setting of index from method export on class ExportData

    Args:
        mock_vol_data (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variable dict
    """
    index = ["OTHER"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(mock_vol_data, name="baretull", table_index=index)
    assert_works(path, index)


def test_set_table_index_not_in_table(mock_vol_data, globalconfig2):
    """Test when setting index with something that is not in data

    Args:
        mock_vol_data (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variables dict
    """
    index = ["banana"]
    exd = ExportData(config=globalconfig2)
    with pytest.raises(KeyError) as k_err:
        exd.export(mock_vol_data, name="baretull", table_index=index)
    assert k_err.value.args[0] == "banana is not in table"


def test_real_sum(edataobj3, drogon_sum_data):

    objdata = _ObjectDataProvider(drogon_sum_data, edataobj3)
    res = objdata._derive_objectdata()
    print("-----------------")
    assert res["table_index"] == ["DATE"], "Incorrect table index "
