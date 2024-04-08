"""Tests for table index"""

from pathlib import Path

import pytest
from fmu.config.utilities import yaml_load
from fmu.dataio import ExportData
from fmu.dataio.providers.objectdata._provider import objectdata_provider_factory


def _read_dict(file_path):
    """Reads text file into dictionary
    Args:
        file_path (string): path to generated file
    Returns:
        dict: contents of file
    """
    file_path = Path(file_path)
    meta_path = file_path.parent / f".{file_path.name}.yml"
    meta = yaml_load(meta_path)
    file_path.unlink()
    meta_path.unlink()
    return meta


def assert_list_and_answer(index, answer, field_to_check):
    """Assert that index is list and the answer is correct

    Args:
        index (should be list): what to check
    """
    type_failure = f"{index} should be list, but is {type(index)}"
    fail_string = f"{field_to_check} should be {answer}, but is {index}"
    assert isinstance(index, list), type_failure
    assert index == answer, fail_string


def assert_correct_table_index(dict_input, answer):
    """does the assert work for all tests

    Args:
        file_path (string): path to generated file
        answer (list): expected answer
    """
    index_name = "table_index"
    meta = dict_input if isinstance(dict_input, dict) else _read_dict(dict_input)

    index = meta["data"][index_name]
    assert_list_and_answer(index, answer, index)


def test_inplace_volume_index(mock_volumes, globalconfig2, monkeypatch, tmp_path):
    """Test volumetric data

    Args:
        mock_volumes (pd.DataFrame): a volumetriclike dataset
        globalconfig2 (dict): one global variables dict
    """
    monkeypatch.chdir(tmp_path)
    answer = ["ZONE", "LICENCE"]
    exd = ExportData(config=globalconfig2, content="volumes")
    path = exd.export(mock_volumes, name="baretull")
    assert_correct_table_index(path, answer)


def test_derive_summary_index_pandas(
    mock_summary, globalconfig2, monkeypatch, tmp_path
):
    """Test summary data

    Args:
        mock_summary (pd.DataFrame): summary "like" dataframe
        globalconfig2 (dict): global variables dict
    """
    monkeypatch.chdir(tmp_path)
    answer = ["DATE"]
    exd = ExportData(config=globalconfig2, content="timeseries")
    path = exd.export(mock_summary, name="baretull")
    assert_correct_table_index(path, answer)


def test_derive_summary_index_pyarrow(
    mock_summary, globalconfig2, monkeypatch, tmp_path
):
    """Test summary data

    Args:
        mock_summary (pd.DataFrame): summary "like" dataframe
        globalconfig2 (dict): global variables dict
    """
    from pyarrow import Table

    monkeypatch.chdir(tmp_path)
    answer = ["DATE"]
    exd = ExportData(config=globalconfig2, content="timeseries")
    path = exd.export(Table.from_pandas(mock_summary), name="baretull")
    assert_correct_table_index(path, answer)


def test_set_from_exportdata(mock_volumes, globalconfig2, monkeypatch, tmp_path):
    """Test setting of index from class ExportData

    Args:
        mock_volumes (pd.DataFrame): a volumetric like dataframe
        globalconfig2 (dict): one global variables dict
    """
    monkeypatch.chdir(tmp_path)
    index = ["OTHER"]
    exd = ExportData(config=globalconfig2, table_index=index, content="timeseries")
    path = exd.export(mock_volumes, name="baretull")
    assert_correct_table_index(path, index)


def test_set_from_export(mock_volumes, globalconfig2, monkeypatch, tmp_path):
    """Test setting of index from method export on class ExportData

    Args:
        mock_volumes (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variable dict
    """
    monkeypatch.chdir(tmp_path)
    index = ["OTHER"]
    exd = ExportData(config=globalconfig2, content="timeseries")
    path = exd.export(mock_volumes, name="baretull", table_index=index)
    assert_correct_table_index(path, index)


def test_set_table_index_not_in_table(
    mock_volumes, globalconfig2, monkeypatch, tmp_path
):
    """Test when setting index with something that is not in data

    Args:
        mock_volumes (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variables dict
    """
    monkeypatch.chdir(tmp_path)
    index = ["banana"]
    exd = ExportData(config=globalconfig2, content="timeseries")
    with pytest.raises(KeyError) as k_err:
        exd.export(mock_volumes, name="baretull", table_index=index)
    assert k_err.value.args[0] == "banana is not in table"


def test_table_index_real_summary(edataobj3, drogon_summary):
    """Test setting of table_index in real summary file

    Args:
        edataobj3 (dict): metadata
        drogon_summary (pd.Dataframe): dataframe with summary data from sumo
    """
    objdata = objectdata_provider_factory(drogon_summary, edataobj3)
    res = objdata.get_objectdata()
    assert res.table_index == ["DATE"], "Incorrect table index "


def test_table_wellpicks(wellpicks, globalconfig1):
    """Test export of wellpicks"""

    exp = ExportData(config=globalconfig1, name="wellpicks", content="wellpicks")

    metadata = exp.generate_metadata(wellpicks)

    assert metadata["data"]["content"] == "wellpicks"

    # table index shall be inserted automatically
    assert metadata["data"]["table_index"] == ["WELL", "HORIZON"]
