"""Test dictionary functionality"""
import os
import json
from pathlib import Path
import yaml
import pytest
from fmu.dataio import ExportData
from fmu.dataio._utils import read_parameters_txt, nested_parameters_dict


@pytest.fixture(name="direct_creation", scope="function")
def _fixture_simple():
    """Return simple dict made here

    Returns:
        dict: the dictionary created
    """
    simple = {"this": "is a test"}
    return simple


@pytest.fixture(name="json_dict", scope="function")
def _fixture_json(fmurun_w_casemetadata):
    """Return dictionary read from json file

    Args:
        fmurun_w_casemetadata (pathlib.Path): path to single fmu realization

    Returns:
        dict: The parameters read from json file
    """
    os.chdir(fmurun_w_casemetadata)
    print(fmurun_w_casemetadata)
    with open(
        fmurun_w_casemetadata / "parameters.json", "r", encoding="utf-8"
    ) as stream:
        json_dict = json.load(stream)
    return json_dict


@pytest.fixture(name="simple_parameters", scope="session")
def _fixture_simple_parameters(fmurun_w_casemetadata):
    """Return dictionary read from parameters.txt

    Args:
        fmurun_w_casemetadata (pathlib.Path): path to single fmu realization

    Returns:
        dict: The parameters read directly from parameters.txt
    """
    return read_parameters_txt(fmurun_w_casemetadata / "parameters.txt")


@pytest.fixture(name="nested_parameters", scope="function")
def _fixture_nested_parameters(simple_parameters):
    """Return dictionary read from parameters.txt and split on : in original key

    Args:
        simple_parameters (dict): dictionary parsed from parameters.txt

    Returns:
        dict: the parameters as nested dictionary
    """
    return nested_parameters_dict(simple_parameters)


def assert_dict_correct(result_dict, meta, name):
    """Assert dictionary and some metadata

    Args:
        result_dict (dict): the dictionaru
        meta (dict): the metadata
        name (str): the name in the metadata
    """
    assert isinstance(result_dict, dict), f"Have not produced dict in test {name}"
    meta_name = meta["data"]["name"]
    assert meta_name == name, f"wrong output name, should be {name} is {meta_name}"
    meta_format = meta["data"]["format"]
    assert meta_format == "json", f"wrong format dict {name} is {meta_format}"


def read_dict_and_meta(path):
    """Return dictionary and metadata produced by dataio

    Args:
        path (str): path to file produced by dataio

    Returns:
        tuple: the dictionary produced with corresponding metadata
    """
    result_dict = None
    with open(path, "r", encoding="utf-8") as stream:
        result_dict = json.load(stream)
    path = Path(path)
    with open(path.parent / f".{path.name}.yml", "r", encoding="utf-8") as meta_stream:
        meta = yaml.load(meta_stream, Loader=yaml.Loader)
    return result_dict, meta


@pytest.mark.parametrize(
    "dictionary",
    [
        ("direct_creation"),
        ("json_dict"),
        ("simple_parameters"),
        ("nested_parameters"),
    ],
)
def test_export_dict_w_meta(globalconfig2, dictionary, request):
    """Test various dictionaries

    Args:
        globalconfig2 (dict): a global variables dictionary
        dictionary (str): name of fixture to use
        request (pytest.fixture): fixture for using fixtures in parameterize
    """
    name = dictionary
    in_dict = request.getfixturevalue(dictionary)
    print(f"{name}: {in_dict}")
    exd = ExportData(config=globalconfig2, content="parameters")
    out_dict, out_meta = read_dict_and_meta(exd.export(in_dict, name=name))
    assert in_dict == out_dict
    assert_dict_correct(out_dict, out_meta, name)


def test_invalid_dict(globalconfig2, drogon_summary, drogon_volumes):
    """Test raising of error when dictionary is not serializable
    Args:
        globalconfig2 (_type_): _description_
        drogon_summary (pd.DataFrame): a dataframe
        drogon_volumes (pa.Table): a pyarrow table
    """
    in_dict = {"volumes": drogon_volumes, "summary": drogon_summary}
    exd = ExportData(config=globalconfig2, content="parameters")
    with pytest.raises(TypeError) as exc_info:
        print(exc_info)
        exd.export(in_dict, name="invalid")
        assert exc_info[1] == "Object of type Table is not JSON serializable"
