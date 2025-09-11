"""Test the utils module"""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pytest
from fmu.datamodels.fmu_results import fields
from xtgeo import Grid, Polygons, RegularSurface

from fmu.dataio import _utils as utils

from ..utils import _get_pydantic_models_from_annotation


@pytest.mark.parametrize(
    "value, result",
    [
        (None, None),
        ("0", 0),
        ("1", 1),
        ("1.0", 1.0),
        ("0.0", 0.0),
        ("-1", -1),
        ("-1.0", -1.0),
        ("-999", -999),
        ("-999.12345678", -999.12345678),
        ("9999999999999999", 9999999999999999),
        ("abc", "abc"),
        (False, False),
        (True, True),
    ],
)
def test_check_if_number(value, result):
    assert utils.check_if_number(value) == result


def test_get_object_name():
    assert utils.get_object_name(object()) is None

    assert utils.get_object_name(RegularSurface(0, 0, 0, 0)) is None
    assert utils.get_object_name(RegularSurface(0, 0, 0, 0, name="unknown")) is None
    assert (
        utils.get_object_name(RegularSurface(0, 0, 0, 0, name="Not ukn")) == "Not ukn"
    )

    assert utils.get_object_name(Polygons()) is None
    assert utils.get_object_name(Polygons(name="poly")) is None
    assert utils.get_object_name(Polygons(name="Not poly")) == "Not poly"

    rng = np.random.default_rng()
    assert (
        utils.get_object_name(
            Grid(
                rng.standard_normal((2, 2, 6)).astype(np.float64),
                rng.standard_normal((2, 2, 2, 4)).astype(np.float32),
                rng.standard_normal((1, 1, 1)).astype(np.int32),
            )
        )
        is None
    )
    assert (
        utils.get_object_name(
            Grid(
                rng.standard_normal((2, 2, 6)).astype(np.float64),
                rng.standard_normal((2, 2, 2, 4)).astype(np.float32),
                rng.standard_normal((1, 1, 1)).astype(np.int32),
                name="noname",
            )
        )
        is None
    )
    assert (
        utils.get_object_name(
            Grid(
                rng.standard_normal((2, 2, 6)).astype(np.float64),
                rng.standard_normal((2, 2, 2, 4)).astype(np.float32),
                rng.standard_normal((1, 1, 1)).astype(np.int32),
                name="Not noname",
            )
        )
        == "Not noname"
    )


def test_non_metadata_export_metadata_file():
    with (
        NamedTemporaryFile(buffering=0, suffix=".yaml") as tf,
        pytest.raises(RuntimeError),
    ):
        utils.export_metadata_file(Path(tf.name), {})


def test_export_file_raises():
    with NamedTemporaryFile() as tf, pytest.raises(TypeError):
        utils.export_file(
            object(),
            Path(tf.name),
            ".placeholder",
        )


def test_create_symlink():
    with pytest.raises(OSError):
        utils.create_symlink(
            "hopefullythispathwillneverexist",
            "norwillthispath",
        )

    with (
        NamedTemporaryFile() as source,
        NamedTemporaryFile() as target,
        pytest.raises(OSError),
    ):
        utils.create_symlink(
            source.name,
            target.name,
        )


def test_generate_description():
    assert utils.generate_description("") is None
    assert utils.generate_description([]) is None
    assert utils.generate_description(None) is None

    assert utils.generate_description("str description") == ["str description"]
    assert utils.generate_description(["str description"]) == ["str description"]

    with pytest.raises(ValueError):
        utils.generate_description({"key": "value"})

    with pytest.raises(ValueError):
        utils.generate_description(object())


def test_read_named_envvar():
    assert utils.read_named_envvar("DONTEXIST") is None

    os.environ["MYTESTENV"] = "mytestvalue"
    assert utils.read_named_envvar("MYTESTENV") == "mytestvalue"


def test_get_pydantic_models_from_annotation():
    annotation = list[fields.Access] | fields.File
    assert _get_pydantic_models_from_annotation(annotation) == [
        fields.Access,
        fields.File,
    ]
    annotation = dict[str, fields.Access] | list[fields.File] | None
    assert _get_pydantic_models_from_annotation(annotation) == [
        fields.Access,
        fields.File,
    ]

    annotation = list[fields.Access | fields.File | fields.Tracklog]
    assert _get_pydantic_models_from_annotation(annotation) == [
        fields.Access,
        fields.File,
        fields.Tracklog,
    ]

    annotation = list[list[list[list[fields.Tracklog]]]]
    assert _get_pydantic_models_from_annotation(annotation) == [fields.Tracklog]

    annotation = str | list[int] | dict[str, int]
    assert not _get_pydantic_models_from_annotation(annotation)
