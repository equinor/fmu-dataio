import datetime
from functools import wraps
from pathlib import Path

import pytest
import yaml


def inside_rms(func):
    @pytest.mark.usefixtures("set_export_data_inside_rms", "set_environ_inside_rms")
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def _parse_yaml(yaml_path):
    """Parse the filename as json, return data"""
    with open(yaml_path, encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    return _isoformat_all_datetimes(data)


def _isoformat_all_datetimes(indate):
    """Recursive function to isoformat all datetimes in a dictionary"""

    if isinstance(indate, list):
        return [_isoformat_all_datetimes(i) for i in indate]

    if isinstance(indate, dict):
        return {key: _isoformat_all_datetimes(indate[key]) for key in indate}

    if isinstance(indate, (datetime.datetime, datetime.date)):
        return indate.isoformat()

    return indate


def _metadata_examples():
    return {
        path.name: _isoformat_all_datetimes(_parse_yaml(path))
        for path in Path(".").absolute().glob("schema/definitions/0.8.0/examples/*.yml")
    }
