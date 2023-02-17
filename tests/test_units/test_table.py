"""Tests for table index
"""
from pathlib import Path
import pyarrow as pa
import pytest
from fmu.dataio import ExportData
from fmu.config.utilities import yaml_load
from fmu.dataio._objectdata_provider import _ObjectDataProvider


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


def test_inplace_volume_index(mock_volumes, globalconfig2):
    """Test volumetric data

    Args:
        mock_volumes (pd.DataFrame): a volumetriclike dataset
        globalconfig2 (dict): one global variables dict
    """
    answer = ["ZONE", "LICENCE"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(mock_volumes, name="baretull")
    assert_works(path, answer)


def test_derive_summary_index_pandas(mock_summary, globalconfig2):
    """Test summary data

    Args:
        mock_summary (pd.DataFrame): summary "like" dataframe
        globalconfig2 (dict): global variables dict
    """
    answer = ["DATE"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(mock_summary, name="baretull")
    assert_works(path, answer)


def test_derive_summary_index_pyarrow(mock_summary, globalconfig2):
    """Test summary data

    Args:
        mock_summary (pd.DataFrame): summary "like" dataframe
        globalconfig2 (dict): global variables dict
    """
    answer = ["DATE"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(pa.Table.from_pandas(mock_summary), name="baretull")
    assert_works(path, answer)


def test_set_from_exportdata(mock_volumes, globalconfig2):
    """Test setting of index from class ExportData

    Args:
        mock_volumes (pd.DataFrame): a volumetric like dataframe
        globalconfig2 (dict): one global variables dict
    """
    index = ["OTHER"]
    exd = ExportData(config=globalconfig2, table_index=index)
    path = exd.export(mock_volumes, name="baretull")
    assert_works(path, index)


def test_set_from_export(mock_volumes, globalconfig2):
    """Test setting of index from method export on class ExportData

    Args:
        mock_volumes (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variable dict
    """
    index = ["OTHER"]
    exd = ExportData(config=globalconfig2)
    path = exd.export(mock_volumes, name="baretull", table_index=index)
    assert_works(path, index)


def test_set_table_index_not_in_table(mock_volumes, globalconfig2):
    """Test when setting index with something that is not in data

    Args:
        mock_volumes (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variables dict
    """
    index = ["banana"]
    exd = ExportData(config=globalconfig2)
    with pytest.raises(KeyError) as k_err:
        exd.export(mock_volumes, name="baretull", table_index=index)
    assert k_err.value.args[0] == "banana is not in table"


def test_real_sum(edataobj3, drogon_summary):
    objdata = _ObjectDataProvider(drogon_summary, edataobj3)
    res = objdata._derive_objectdata()
    print("-----------------")
    assert res["table_index"] == ["DATE"], "Incorrect table index "
