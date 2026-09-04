from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_args

import yaml
from fmu.datamodels.context.mappings import DataSystem
from fmu.settings.models.mappings import (
    InternalRelationType,
    InternalWellboreIdentifierMapping,
    InternalWellboreMappings,
)
from pydantic import BaseModel

if TYPE_CHECKING:
    from fmu.settings import ProjectFMUDirectory

YamlLike = (
    dict[str, Any]
    | list[Any]
    | datetime.datetime
    | datetime.date
    | str
    | int
    | float
    | bool
    | None
)


def add_wellbore_mappings(fmu_dir: ProjectFMUDirectory) -> None:
    """Add representative RMS wellbore mappings to an FMU directory."""
    source_id = "RFT_30_9-B-21_C"
    fmu_dir.mappings.update_internal_wellbore_mappings(
        InternalWellboreMappings(
            root=[
                InternalWellboreIdentifierMapping(
                    source_system=DataSystem.rms,
                    target_system=DataSystem.rms,
                    relation_type=InternalRelationType.primary,
                    source_id=source_id,
                    target_id=source_id,
                ),
                InternalWellboreIdentifierMapping(
                    source_system=DataSystem.rms,
                    target_system=DataSystem.smda,
                    relation_type=InternalRelationType.primary,
                    source_id=source_id,
                    target_id="NO 30/9-B-21 C",
                ),
                InternalWellboreIdentifierMapping(
                    source_system=DataSystem.rms,
                    target_system=DataSystem.simulator,
                    relation_type=InternalRelationType.primary,
                    source_id=source_id,
                    target_id="B21C",
                ),
            ]
        )
    )


def _parse_yaml(yaml_path: str | Path) -> YamlLike:
    """Parse the filename as json, return data"""
    with open(yaml_path, encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    return _isoformat_all_datetimes(data)


def _isoformat_all_datetimes(indate: YamlLike) -> YamlLike:
    """Recursive function to isoformat all datetimes in a dictionary"""

    if isinstance(indate, list):
        return [_isoformat_all_datetimes(i) for i in indate]

    if isinstance(indate, dict):
        return {key: _isoformat_all_datetimes(indate[key]) for key in indate}

    if isinstance(indate, datetime.datetime | datetime.date):
        return indate.isoformat()

    return indate


def _metadata_examples() -> dict[str, Any]:
    return {
        path.name: _isoformat_all_datetimes(_parse_yaml(path))
        for path in Path(".").absolute().glob("examples/example_metadata/*.yml")
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
