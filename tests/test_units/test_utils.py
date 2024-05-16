"""Test the utils module"""

import pytest
from fmu.dataio import _utils as utils

from ..utils import inside_rms


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


@inside_rms
def test_detect_inside_rms_decorator():
    assert utils.detect_inside_rms()


def test_detect_not_inside_rms():
    assert not utils.detect_inside_rms()


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
