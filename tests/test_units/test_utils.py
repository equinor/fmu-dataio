"""Test the utils module"""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from fmu.datamodels.common.access import Access
from fmu.datamodels.common.tracklog import Tracklog
from fmu.datamodels.fmu_results import fields

from fmu.dataio import _utils as utils

from ..utils import _get_pydantic_models_from_annotation


def test_non_metadata_export_metadata_file() -> None:
    with (
        NamedTemporaryFile(buffering=0, suffix=".yaml") as tf,
        pytest.raises(RuntimeError),
    ):
        utils.export_metadata_file(Path(tf.name), {})


def test_export_file_raises() -> None:
    with NamedTemporaryFile() as tf, pytest.raises(TypeError):
        utils.export_file(
            object(),
            Path(tf.name),
            ".placeholder",
        )


def test_get_pydantic_models_from_annotation():
    annotation = list[Access] | fields.File
    assert _get_pydantic_models_from_annotation(annotation) == [
        Access,
        fields.File,
    ]
    annotation = dict[str, Access] | list[fields.File] | None
    assert _get_pydantic_models_from_annotation(annotation) == [
        Access,
        fields.File,
    ]

    annotation = list[Access | fields.File | Tracklog]
    assert _get_pydantic_models_from_annotation(annotation) == [
        Access,
        fields.File,
        Tracklog,
    ]

    annotation = list[list[list[list[Tracklog]]]]
    assert _get_pydantic_models_from_annotation(annotation) == [Tracklog]

    annotation = str | list[int] | dict[str, int]
    assert not _get_pydantic_models_from_annotation(annotation)
