from fmu.dataio import ExportData
from pathlib import Path
import json
import yaml


def test_export_dict(globalconfig2):
    test_dict = {"testing": "yes"}
    exd = ExportData(config=globalconfig2)
    out_name = "baretull"
    path = exd.export(test_dict, name=out_name)
    result_dict = None
    with open(path, "r") as stream:
        result_dict = json.load(stream)
    assert isinstance(result_dict, dict), "Have not produced json"
    path = Path(path)
    with open(path.parent / f".{path.name}.yml", "r") as meta_stream:
        meta = yaml.load(meta_stream, Loader=yaml.Loader)
    assert meta["data"]["name"] == out_name, "wrong output name"
    assert meta["data"]["format"] == "json"
