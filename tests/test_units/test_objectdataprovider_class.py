"""Test the _ObjectData class from the _objectdata.py module"""

import os

import fmu.dataio as dataio
import pytest
from fmu.dataio._definitions import ConfigurationError, ValidFormats
from fmu.dataio.providers.objectdata._provider import (
    objectdata_provider_factory,
)
from fmu.dataio.providers.objectdata._xtgeo import RegularSurfaceDataProvider

from ..conftest import remove_ert_env, set_ert_env_prehook
from ..utils import inside_rms

# --------------------------------------------------------------------------------------
# RegularSurface
# --------------------------------------------------------------------------------------


def test_objectdata_regularsurface_derive_named_stratigraphy(regsurf, edataobj1):
    """Get name and some stratigaphic keys for a valid RegularSurface object ."""
    # mimic the stripped parts of configuations for testing here
    objdata = objectdata_provider_factory(regsurf, edataobj1)

    res = objdata._get_named_stratigraphy()

    assert res.name == "Whatever Top"
    assert "TopWhatever" in res.alias
    assert res.stratigraphic is True


def test_objectdata_regularsurface_get_named_stratigraphy_differ(regsurf, edataobj2):
    """Get name and some stratigaphic keys for a valid RegularSurface object ."""
    # mimic the stripped parts of configuations for testing here
    objdata = objectdata_provider_factory(regsurf, edataobj2)

    res = objdata._get_named_stratigraphy()

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

    assert specs.ncol == regsurf.ncol
    assert bbox.xmin == 0.0
    assert bbox.zmin == 1234.0


def test_objectdata_regularsurface_derive_objectdata(regsurf, edataobj1):
    """Derive other properties."""

    objdata = objectdata_provider_factory(regsurf, edataobj1)
    assert isinstance(objdata, RegularSurfaceDataProvider)
    assert objdata.classname.value == "surface"

    res = objdata.get_objectdata()
    assert res.subtype == "RegularSurface"
    assert res.extension == ".gri"


def test_objectdata_regularsurface_derive_metadata(regsurf, edataobj1):
    """Derive all metadata for the 'data' block in fmu-dataio."""

    myobj = objectdata_provider_factory(regsurf, edataobj1)
    assert myobj._metadata["content"] == "depth"
    assert myobj._metadata["alias"]


def test_objectdata_provider_factory_raises_on_unknown(edataobj1):
    with pytest.raises(NotImplementedError, match="not currently supported"):
        objectdata_provider_factory(object(), edataobj1)


def test_regsurf_preprocessed_observation(
    fmurun_prehook, rmssetup, rmsglobalconfig, regsurf, monkeypatch
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

    def _run_case_fmu(fmurun_prehook, rmsglobalconfig, surfacepath):
        """Run FMU workflow, using the preprocessed data as case data.

        When re-using metadata, the input object to dataio shall not be a XTGeo or
        Pandas or ... instance, but just a file path (either as string or a pathlib.Path
        object). This is because we want to avoid time and resources spent on double
        reading e.g. a seismic cube, but rather trigger a file copy action instead.

        But it requires that valid metadata for that file is found. The rule for
        merging is currently defaulted to "preprocessed".
        """
        os.chdir(fmurun_prehook)

        casepath = fmurun_prehook
        edata = dataio.ExportPreprocessedData(
            config=rmsglobalconfig,
            is_observation=True,
            casepath=casepath,
        )
        return edata.generate_metadata(surfacepath)

    # run two stage process
    remove_ert_env(monkeypatch)
    edata, mysurf = _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf)
    set_ert_env_prehook(monkeypatch)
    case_meta = _run_case_fmu(fmurun_prehook, rmsglobalconfig, mysurf)
    assert edata._metadata["data"] == case_meta["data"]
