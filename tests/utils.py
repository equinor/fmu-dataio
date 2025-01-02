from __future__ import annotations

import datetime
from functools import wraps
from pathlib import Path
from typing import Any, get_args

import pytest
import yaml
from pydantic import BaseModel


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
        for path in Path(".").absolute().glob("examples/0.8.0/*.yml")
    }


def _get_pydantic_models_from_annotation(annotation: Any) -> list[Any]:
    """
    Get a list of all pydantic models defined inside an annotation.
    Example: Union[Model1, list[dict[str, Model2]]] returns [Model1, Model2]
    """
    if isinstance(annotation, type(BaseModel)):
        return [annotation]

    annotations = []
    for ann in get_args(annotation):
        annotations += _get_pydantic_models_from_annotation(ann)
    return annotations


def _get_nested_pydantic_models(model: type[BaseModel]) -> set[type[BaseModel]]:
    """Get a set of all nested pydantic models from a pydantic model"""
    models = {model}

    for field_info in model.model_fields.values():
        for model in _get_pydantic_models_from_annotation(field_info.annotation):
            if model not in models:
                models.update(_get_nested_pydantic_models(model))
    return models
