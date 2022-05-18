"""Test the _ObjectData class from the _objectdata.py module"""
import pytest

from fmu.dataio._definitions import _ValidFormats
from fmu.dataio._objectdata_provider import ConfigurationError, _ObjectDataProvider

# --------------------------------------------------------------------------------------
# RegularSurface
# --------------------------------------------------------------------------------------


def test_objectdata_regularsurface_derive_name_stratigraphy(regsurf, edataobj1):
    """Get name and some stratigaphic keys for a valid RegularSurface object ."""
    # mimic the stripped parts of configuations for testing here
    objdata = _ObjectDataProvider(regsurf, edataobj1)

    res = objdata._derive_name_stratigraphy()

    assert res["name"] == "Whatever Top"
    assert "TopWhatever" in res["alias"]
    assert res["stratigraphic"] is True


def test_objectdata_regularsurface_derive_name_stratigraphy_differ(regsurf, edataobj2):
    """Get name and some stratigaphic keys for a valid RegularSurface object ."""
    # mimic the stripped parts of configuations for testing here
    objdata = _ObjectDataProvider(regsurf, edataobj2)

    res = objdata._derive_name_stratigraphy()

    assert res["name"] == "VOLANTIS GP. Top"
    assert "TopVolantis" in res["alias"]
    assert res["stratigraphic"] is True


def test_objectdata_regularsurface_validate_extension(regsurf, edataobj1):
    """Test a valid extension for RegularSurface object."""

    ext = _ObjectDataProvider(regsurf, edataobj1)._validate_get_ext(
        "irap_binary", "RegularSurface", _ValidFormats().surface
    )

    assert ext == ".gri"


def test_objectdata_regularsurface_validate_extension_shall_fail(regsurf, edataobj1):
    """Test an invalid extension for RegularSurface object."""

    with pytest.raises(ConfigurationError):
        _ = _ObjectDataProvider(regsurf, edataobj1)._validate_get_ext(
            "some_invalid", "RegularSurface", _ValidFormats().surface
        )


def test_objectdata_regularsurface_spec_bbox(regsurf, edataobj1):
    """Derive specs and bbox for RegularSurface object."""

    specs, bbox = _ObjectDataProvider(
        regsurf, edataobj1
    )._derive_spec_bbox_regularsurface()

    assert specs["ncol"] == regsurf.ncol
    assert bbox["xmin"] == 0.0
    assert bbox["zmin"] == 1234.0


def test_objectdata_regularsurface_derive_objectdata(regsurf, edataobj1):
    """Derive other properties."""

    res = _ObjectDataProvider(regsurf, edataobj1)._derive_objectdata()

    assert res["subtype"] == "RegularSurface"
    assert res["classname"] == "surface"
    assert res["extension"] == ".gri"


def test_objectdata_regularsurface_derive_metadata(regsurf, edataobj1):
    """Derive all metadata for the 'data' block in fmu-dataio."""

    myobj = _ObjectDataProvider(regsurf, edataobj1)
    myobj.derive_metadata()
    res = myobj.metadata
    assert res["content"] == "depth"

    assert res["alias"]
