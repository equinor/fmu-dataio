"""Tests for table index"""

from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from fmu.config.utilities import yaml_load
from fmu.dataio import ExportData
from fmu.dataio._definitions import STANDARD_TABLE_INDEX_COLUMNS, StandardTableIndex
from fmu.dataio._models.fmu_results.enums import Content
from fmu.dataio.providers.objectdata._provider import objectdata_provider_factory
from fmu.dataio.providers.objectdata._tables import _derive_index


def _read_dict(file_path: str) -> None:
    """Reads text file into dictionary
    Args:
        file_path (string): path to generated file
    Returns:
        dict: contents of file
    """
    path = Path(file_path)
    meta_path = path.parent / f".{path.name}.yml"
    meta = yaml_load(meta_path)
    path.unlink()
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


@pytest.mark.skip_inside_rmsvenv
def test_inplace_volume_index(mock_volumes, globalconfig2, monkeypatch, tmp_path):
    """Test volumetric data

    Args:
        mock_volumes (pd.DataFrame): a volumetriclike dataset
        globalconfig2 (dict): one global variables dict
    """

    # TODO: Refactor tests and move away from outside/inside rms pattern

    monkeypatch.chdir(tmp_path)
    answer = ["FLUID", "ZONE", "LICENSE"]
    exd = ExportData(config=globalconfig2, content="volumes", name="baretull")
    path = exd.export(mock_volumes)
    assert_correct_table_index(path, answer)


@pytest.mark.skip_inside_rmsvenv
def test_relperm_index(mock_relperm, globalconfig2, monkeypatch, tmp_path):
    """Test that the table index is set correct for relperm data"""
    monkeypatch.chdir(tmp_path)
    answer = ["SATNUM"]
    exd = ExportData(config=globalconfig2, content="relperm", name="baretull")
    path = exd.export(mock_relperm)
    assert_correct_table_index(path, answer)


@pytest.mark.skip_inside_rmsvenv
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
    exd = ExportData(
        config=globalconfig2, content="simulationtimeseries", name="baretull"
    )
    path = exd.export(mock_summary)
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
    exd = ExportData(
        config=globalconfig2, content="simulationtimeseries", name="baretull"
    )
    path = exd.export(Table.from_pandas(mock_summary))
    assert_correct_table_index(path, answer)


def test_set_from_exportdata(mock_volumes, globalconfig2, monkeypatch, tmp_path):
    """Test setting of index from class ExportData

    Args:
        mock_volumes (pd.DataFrame): a volumetric like dataframe
        globalconfig2 (dict): one global variables dict
    """
    monkeypatch.chdir(tmp_path)
    index = ["OTHER"]
    exd = ExportData(
        config=globalconfig2, table_index=index, content="timeseries", name="baretull"
    )
    path = exd.export(mock_volumes)
    assert_correct_table_index(path, index)


def test_set_from_export(mock_volumes, globalconfig2, monkeypatch, tmp_path):
    """Test setting of index from method export on class ExportData

    Args:
        mock_volumes (pd.DataFrame): volumetric like data
        globalconfig2 (dict): one global variable dict
    """
    monkeypatch.chdir(tmp_path)
    index = ["OTHER"]
    exd = ExportData(
        config=globalconfig2, content="timeseries", table_index=index, name="baretull"
    )
    path = exd.export(mock_volumes)
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
    exd = ExportData(
        config=globalconfig2, content="timeseries", table_index=index, name="baretull"
    )
    with pytest.raises(KeyError) as k_err:
        exd.export(mock_volumes)
    assert "are not present" in k_err.value.args[0]


def test_table_index_timeseries(export_data_obj_timeseries, drogon_summary):
    """Test setting of table_index in an arbitrary timeseries.

    Args:
        edataobj3 (dict): metadata
        drogon_summary (pd.Dataframe): dataframe with summary data from sumo
    """
    objdata = objectdata_provider_factory(drogon_summary, export_data_obj_timeseries)
    assert objdata.table_index == ["DATE"], "Incorrect table index "


def test_table_index_real_summary(edataobj3, drogon_summary):
    """Test setting of table_index in real summary file

    Args:
        edataobj3 (dict): metadata
        drogon_summary (pd.Dataframe): dataframe with summary data from sumo
    """
    objdata = objectdata_provider_factory(drogon_summary, edataobj3)
    assert objdata.table_index == ["DATE"], "Incorrect table index "


def test_table_wellpicks(wellpicks, globalconfig1):
    """Test export of wellpicks"""

    exp = ExportData(config=globalconfig1, name="wellpicks", content="wellpicks")

    metadata = exp.generate_metadata(wellpicks)

    assert metadata["data"]["content"] == "wellpicks"

    # table index shall be inserted automatically
    assert metadata["data"]["table_index"] == ["WELL", "HORIZON"]


def test_standard_table_index_valid():
    """Test the StandardTableIndex model"""
    index = StandardTableIndex(
        columns=["col1", "col2"],
        required=["col1"],
    )
    assert index.columns == ["col1", "col2"]
    assert index.required == ["col1"]

    # should raise if a required column is not listed in columns
    with pytest.raises(ValidationError):
        StandardTableIndex(
            columns=["col1", "col2"],
            required=["col3"],
        )


def test_derive_index_from_input_valid():
    """Test providing a valid table index"""
    table_index = ["col1", "col2"]
    table_columns = ["col1", "col2", "col3"]
    result = _derive_index(table_columns, table_index)
    assert result == table_index


def test_derive_index_from_input_invalid():
    """Test that error is raised if missing column"""
    table_index = ["col1", "col4"]
    table_columns = ["col1", "col2", "col3"]
    with pytest.raises(KeyError, match="col4"):
        _derive_index(table_columns, table_index)


def test_derive_index_from_input_non_standard():
    """Test that warning is given if a column that a non-standard column is provided"""
    content = Content.volumes
    table_index = ["col1"]
    table_columns = STANDARD_TABLE_INDEX_COLUMNS[content].columns + ["col1"]
    with pytest.warns(FutureWarning, match="standard"):
        result = _derive_index(table_columns, table_index, content)
    assert result == table_index


def test_derive_index_from_standard():
    """
    Test that when table index is not provided the index is set to the
    standard for the content.
    """
    content = Content.timeseries
    table_index = None
    table_columns = STANDARD_TABLE_INDEX_COLUMNS[content].columns + ["col1"]
    result = _derive_index(table_columns, table_index, content)
    assert result == STANDARD_TABLE_INDEX_COLUMNS[content].columns


def test_derive_index_from_standard_missing_columns():
    """
    Test that when table index is not provided a Futurewarning is given
    if not all columns standard index columns are present in the table
    """
    content = Content.volumes
    assert content in STANDARD_TABLE_INDEX_COLUMNS
    table_index = None
    table_columns = ["ZONE"]  # only subset of required
    with pytest.warns(FutureWarning, match="standard"):
        result = _derive_index(table_columns, table_index, content)
    assert result == table_columns


def test_derive_index_legacy():
    """
    Test that when table index is not provided and content is not
    defined with standard table index columns, a FutureWarning is given
    and columns registered as a standard index column is returned.
    """
    content = Content.depth
    assert content not in STANDARD_TABLE_INDEX_COLUMNS
    table_index = None
    table_columns = ["WELL", "SATNUM", "REGION", "col1"]
    with pytest.warns(FutureWarning):
        result = _derive_index(table_columns, table_index, content=content)
    assert set(result) == {"WELL", "SATNUM", "REGION"}


def test_table_index_in_metadata_with_table_index(globalconfig2, mock_volumes):
    """Test providing a valid table index"""
    table_index = ["ZONE"]
    with pytest.warns(FutureWarning, match="standard"):
        meta = ExportData(
            config=globalconfig2,
            content="volumes",
            name="geogrid",
            table_index=table_index,
        ).generate_metadata(mock_volumes)

    assert meta["data"]["table_index"] == table_index


def test_table_index_in_metadata_from_standard(globalconfig2, mock_volumes):
    """
    Test that when table index is not provided the index is set to the
    standard for the content.
    """
    content = Content.volumes
    assert content in STANDARD_TABLE_INDEX_COLUMNS
    meta = ExportData(
        config=globalconfig2,
        content=content,
        name="geogrid",
    ).generate_metadata(mock_volumes)

    expected = [
        x for x in STANDARD_TABLE_INDEX_COLUMNS[content].columns if x in mock_volumes
    ]
    assert meta["data"]["table_index"] == expected


def test_table_index_in_metadata_legacy_fallback(globalconfig2):
    """
    Test that when table index is not provided and content is not
    defined with standard table index columns, a FutureWarning is given
    and columns registered as a standard index column is returned.
    """
    content = Content.depth
    assert content not in STANDARD_TABLE_INDEX_COLUMNS
    mock_table = pd.DataFrame(
        {
            "DATE": ["B", "A", "C"],
            "well": ["L3", "L2", "L1"],
            "SATNUM": ["oil", "gas", "water"],
            "data": [1, 2, 3],
        }
    )
    with pytest.warns(FutureWarning):
        meta = ExportData(
            config=globalconfig2,
            content=content,
            name="myname",
        ).generate_metadata(mock_table)

    assert set(meta["data"]["table_index"]) == {"DATE", "well", "SATNUM"}
