"""Test the utils module"""

import pytest

from fmu.dataio import _utils as utils


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


def test_uuid_from_string():
    """Test the uuid_from_string method."""
    result = utils.uuid_from_string("mystring")
    assert len(result) == 36
    assert isinstance(result, str)

    # test repeatability
    first = utils.uuid_from_string("mystring")
    second = utils.uuid_from_string("mystring")

    assert first == second
