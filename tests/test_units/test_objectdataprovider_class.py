"""Test the _ObjectData class from the _objectdata.py module"""

import os
from datetime import datetime

import pytest
from fmu.dataio import dataio
from fmu.dataio._definitions import ConfigurationError, ValidFormats
from fmu.dataio.providers.objectdata._base import (
    get_timedata_from_existing,
)
from fmu.dataio.providers.objectdata._provider import (
    objectdata_provider_factory,
)
from fmu.dataio.providers.objectdata._xtgeo import RegularSurfaceDataProvider

from ..utils import inside_rms


@pytest.mark.parametrize(
    "given, expected",
    (
        (
            {"t0": {"value": "2022-08-02T00:00:00", "label": "base"}},
            (datetime.strptime("2022-08-02T00:00:00", "%Y-%m-%dT%H:%M:%S"), None),
        ),
        (
            [
                {"value": "2030-01-01T00:00:00", "label": "moni"},
                {"value": "2010-02-03T00:00:00", "label": "base"},
            ],
            (
                datetime.strptime("2030-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S"),
                datetime.strptime("2010-02-03T00:00:00", "%Y-%m-%dT%H:%M:%S"),
            ),
        ),
    ),
)
def test_get_timedata_from_existing(given: dict, expected: tuple):
    assert get_timedata_from_existing(given) == expected


# --------------------------------------------------------------------------------------
# RegularSurface
# --------------------------------------------------------------------------------------


def test_objectdata_regularsurface_derive_name_stratigraphy(regsurf, edataobj1):
    """Get name and some stratigaphic keys for a valid RegularSurface object ."""
    # mimic the stripped parts of configuations for testing here
    objdata = objectdata_provider_factory(regsurf, edataobj1)

    res = objdata._derive_name_stratigraphy()

    assert res.name == "Whatever Top"
    assert "TopWhatever" in res.alias
    assert res.stratigraphic is True


def test_objectdata_regularsurface_derive_name_stratigraphy_differ(regsurf, edataobj2):
    """Get name and some stratigaphic keys for a valid RegularSurface object ."""
    # mimic the stripped parts of configuations for testing here
    objdata = objectdata_provider_factory(regsurf, edataobj2)

    res = objdata._derive_name_stratigraphy()

    assert res.name == "VOLANTIS GP. Top"
    assert "TopVolantis" in res.alias
    assert res.stratigraphic is True


def test_objectdata_regularsurface_validate_extension(regsurf, edataobj1):
    """Test a valid extension for RegularSurface object."""

    ext = objectdata_provider_factory(regsurf, edataobj1)._validate_get_ext(
        "irap_binary", "RegularSurface", ValidFormats().surface
    )

    assert ext == ".gri"


def test_objectdata_regularsurface_validate_extension_shall_fail(regsurf, edataobj1):
    """Test an invalid extension for RegularSurface object."""

    with pytest.raises(ConfigurationError):
        objectdata_provider_factory(regsurf, edataobj1)._validate_get_ext(
            "some_invalid", "RegularSurface", ValidFormats().surface
        )


def test_objectdata_regularsurface_spec_bbox(regsurf, edataobj1):
    """Derive specs and bbox for RegularSurface object."""

    objdata = objectdata_provider_factory(regsurf, edataobj1)
    specs = objdata.get_spec()
    bbox = objdata.get_bbox()

    assert specs["ncol"] == regsurf.ncol
    assert bbox["xmin"] == 0.0
    assert bbox["zmin"] == 1234.0


def test_objectdata_regularsurface_derive_objectdata(regsurf, edataobj1):
    """Derive other properties."""

    objdata = objectdata_provider_factory(regsurf, edataobj1)
    assert isinstance(objdata, RegularSurfaceDataProvider)

    res = objdata.get_objectdata()
    assert res.subtype == "RegularSurface"
    assert res.classname == "surface"
    assert res.extension == ".gri"


def test_objectdata_regularsurface_derive_metadata(regsurf, edataobj1):
    """Derive all metadata for the 'data' block in fmu-dataio."""

    myobj = objectdata_provider_factory(regsurf, edataobj1)
    myobj.derive_metadata()
    res = myobj.metadata
    assert res["content"] == "depth"
    assert res["alias"]


def test_objectdata_provider_factory_raises_on_unknown(edataobj1):
    with pytest.raises(NotImplementedError, match="not currently supported"):
        objectdata_provider_factory(object(), edataobj1)


def test_regsurf_preprocessed_observation(
    fmurun_w_casemetadata, rmssetup, rmsglobalconfig, regsurf
):
    """Test generating pre-realization surfaces that comes to share/preprocessed.

    Later, a fmu run will update this (merge metadata)
    """

    @inside_rms
    def _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf):
        """Run an export of a preprocessed surface inside RMS."""

        os.chdir(rmssetup)
        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            fmu_context="preprocessed",
            name="TopVolantis",
            content="depth",
            is_observation=True,
            timedata=[[20240802, "moni"], [20200909, "base"]],
        )
        return edata, edata.export(regsurf)

    def _run_case_fmu(fmurun_w_casemetadata, rmsglobalconfig, surfacepath):
        """Run FMU workflow, using the preprocessed data as case data.

        When re-using metadata, the input object to dataio shall not be a XTGeo or
        Pandas or ... instance, but just a file path (either as string or a pathlib.Path
        object). This is because we want to avoid time and resources spent on double
        reading e.g. a seismic cube, but rather trigger a file copy action instead.

        But it requires that valid metadata for that file is found. The rule for
        merging is currently defaulted to "preprocessed".
        """
        os.chdir(fmurun_w_casemetadata)

        casepath = fmurun_w_casemetadata.parent.parent
        edata = dataio.ExportData(
            config=rmsglobalconfig,
            fmu_context="case",
            content=None,
            is_observation=True,
        )
        return edata.generate_metadata(
            surfacepath,
            casepath=casepath,
        )

    # run two stage process
    edata, mysurf = _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf)
    case_meta = _run_case_fmu(fmurun_w_casemetadata, rmsglobalconfig, mysurf)
    assert edata._metadata["data"] == case_meta["data"]
