"""Test the functions of the utils.py module"""

import pytest

from fmu.dataio import _utils as utils


def test_detect_inside_rms():

    # TODO

    pass


def test_drop_nones():

    # TODO

    pass


def test_export_metadata_file():

    # TODO

    pass


def test_export_file():

    # TODO

    pass


def test_md5sum():

    # TODO

    pass


def test_export_file_compute_checksum_md5():

    # TODO

    pass


def test_uuid_from_string():

    # TODO

    pass


def test_read_parameters_txt():

    # TODO

    pass


def test_nested_parameters_dict():

    # TODO

    pass


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
def test_str2number(value, result):
    assert utils.str2number(value) == result


def test_get_object_name():

    # TODO

    pass


def test_load_yaml():

    # TODO

    pass


def test_filter_validate_metadata():

    # TODO

    pass


def test_validate_description():

    # TODO

    pass


def test_str2bool():

    # TODO

    pass


def test_pyarrow_field_to_dict():

    # TODO

    pass
