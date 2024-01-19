"""Test the utils module"""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pytest
from conftest import set_environ_inside_rms_flag
from fmu.dataio import _utils as utils
from xtgeo import Grid, Polygons, RegularSurface


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


@pytest.mark.parametrize(
    "given, expected, isoformat",
    (
        (
            {},
            (None, None),
            True,
        ),
        (
            {"time": {"t0": {"value": "2022-08-02T00:00:00", "label": "base"}}},
            ("2022-08-02T00:00:00", None),
            True,
        ),
        (
            {
                "time": [
                    {"value": "2030-01-01T00:00:00", "label": "moni"},
                    {"value": "2010-02-03T00:00:00", "label": "base"},
                ]
            },
            ("2030-01-01T00:00:00", "2010-02-03T00:00:00"),
            True,
        ),
        (
            {},
            (None, None),
            False,
        ),
        (
            {"time": {"t0": {"value": "2022-08-02T00:00:00", "label": "base"}}},
            ("20220802", None),
            False,
        ),
        (
            {
                "time": [
                    {"value": "2030-01-01T00:00:00", "label": "moni"},
                    {"value": "2010-02-03T00:00:00", "label": "base"},
                ]
            },
            ("20300101", "20100203"),
            False,
        ),
    ),
)
def test_parse_timedata(given: dict, expected: tuple, isoformat: bool):
    assert utils.parse_timedata(given, isoformat) == expected


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

    assert (
        utils.get_object_name(
            Grid(
                np.random.randn(2, 2, 6).astype(np.float64),
                np.random.randn(2, 2, 2, 4).astype(np.float32),
                np.random.randn(1, 1, 1).astype(np.int32),
            )
        )
        is None
    )
    assert (
        utils.get_object_name(
            Grid(
                np.random.randn(2, 2, 6).astype(np.float64),
                np.random.randn(2, 2, 2, 4).astype(np.float32),
                np.random.randn(1, 1, 1).astype(np.int32),
                name="noname",
            )
        )
        is None
    )
    assert (
        utils.get_object_name(
            Grid(
                np.random.randn(2, 2, 6).astype(np.float64),
                np.random.randn(2, 2, 2, 4).astype(np.float32),
                np.random.randn(1, 1, 1).astype(np.int32),
                name="Not noname",
            )
        )
        == "Not noname"
    )


def test_detect_inside_rms():
    assert not utils.detect_inside_rms()
    with set_environ_inside_rms_flag():
        assert utils.detect_inside_rms()


def test_non_metadata_export_metadata_file():
    with NamedTemporaryFile(buffering=0, suffix=".yaml") as tf, pytest.raises(
        RuntimeError
    ):
        utils.export_metadata_file(Path(tf.name), {}, savefmt="json")

    with NamedTemporaryFile(buffering=0, suffix=".yaml") as tf, pytest.raises(
        RuntimeError
    ):
        utils.export_metadata_file(Path(tf.name), {}, savefmt="yaml")


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

    with NamedTemporaryFile() as source, NamedTemporaryFile() as target, pytest.raises(
        OSError
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
