import pytest

from fmu.dataio._models.fmu_results.enums import Content


def test_content_missing():
    with pytest.raises(ValueError, match="Invalid 'content'"):
        Content("invalid_content")


def test_content_from_string():
    assert Content._from_content("depth") == Content.depth


def test_content_from_dict():
    assert Content._from_content({"depth": {}}) == Content.depth


def test_content_from_invalid_dict():
    with pytest.raises(ValueError, match="Incorrect format found for 'content'"):
        Content._from_content(None)
