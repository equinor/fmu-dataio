"""Test the dataio running with pre-realization objects, e.g. surfaces.

These outputs may need an active 'fmu_context' key in order to come into the right
folder and classification, but there are various ways to to this:

1) Have files in a folder without any metadata; cf fmu_context="case"
2) Have files with pregenerated matadata in a folder; cf fmu_context="preprocessed"

These objects are normally made as hook workflows before ERT has ran any forward jobs
and are typically used to compare results.
"""

import logging
import os

import fmu.dataio as dataio
import pytest
from fmu.dataio import _utils as utils

from ..conftest import remove_ert_env, set_ert_env_prehook
from ..utils import inside_rms

logger = logging.getLogger(__name__)


def test_regsurf_case_observation(fmurun_prehook, rmsglobalconfig, regsurf):
    """Test generating pre-realization surfaces that comes right to case.

    Notice the difference between this use-case and the 'preprocessed' example later!
    """
    logger.info("Active folder is %s", fmurun_prehook)

    os.chdir(fmurun_prehook)

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
        fmu_context="case",
        casepath=fmurun_prehook,
        name="mymap",
        content="depth",
        is_observation=True,
    )

    metadata = edata.generate_metadata(regsurf)
    logger.debug("\n%s", utils.prettyprint_dict(metadata))
    assert (
        "ertrun1/share/observations/maps/mymap.gri" in metadata["file"]["absolute_path"]
    )

    exp = edata.export(regsurf)
    assert "ertrun1/share/observations/maps/mymap.gri" in exp


def test_regsurf_preprocessed_observation(
    fmurun_prehook, rmssetup, rmsglobalconfig, regsurf, monkeypatch
):
    """Test generating pre-realization surfaces that comes to share/preprocessed.

    Later, a fmu run will update this (merge metadata)
    """

    @inside_rms
    def _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf):
        """Run an export of a preprocessed surface inside RMS."""
        logger.info("Active folder is %s", rmssetup)

        os.chdir(rmssetup)
        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            fmu_context="preprocessed",
            name="TopVolantis",
            content="depth",
            is_observation=True,
            timedata=[[20240802, "moni"], [20200909, "base"]],
        )

        metadata = edata.generate_metadata(regsurf)
        logger.debug("\n%s", utils.prettyprint_dict(metadata))

        assert (
            metadata["file"]["relative_path"]
            == "share/preprocessed/maps/topvolantis--20240802_20200909.gri"
        )
        assert metadata["data"]["name"] == "VOLANTIS GP. Top"
        assert "_preprocessed" in metadata

        return edata.export(regsurf)

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
        logger.info("Active folder is %s", fmurun_prehook)

        casepath = fmurun_prehook

        edata = dataio.ExportPreprocessedData(
            config=rmsglobalconfig,  # read from global config
            is_observation=True,
            casepath=casepath,
        )
        metadata = edata.generate_metadata(surfacepath)
        logger.info("Casepath folder is now %s", casepath)
        logger.debug("\n%s", utils.prettyprint_dict(metadata))
        assert (
            metadata["file"]["relative_path"]
            == "share/observations/maps/topvolantis--20240802_20200909.gri"
        )
        assert "merged" in metadata["tracklog"][-1]["event"]
        assert metadata["data"]["name"] == "VOLANTIS GP. Top"
        assert "TopVolantis" in metadata["data"]["alias"]
        assert "_preprocessed" not in metadata
        # check that content comes from the existing metadata
        assert metadata["data"]["content"] == "depth"

        # do the actual export (which will copy data to case/share/observations/...)
        edata.export(surfacepath)
        assert (
            casepath
            / "share"
            / "observations"
            / "maps"
            / ".topvolantis--20240802_20200909.gri.yml"
        ).exists()

    # run two stage process
    remove_ert_env(monkeypatch)
    mysurf = _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf)
    set_ert_env_prehook(monkeypatch)
    _run_case_fmu(fmurun_prehook, rmsglobalconfig, mysurf)

    logger.info("Preprocessed surface is %s", mysurf)


@pytest.mark.parametrize(
    "parent, name, tagname, exproot",
    [
        ("", "myname", "", "myname"),
        ("parent", "myname", "", "parent--myname"),
        ("parent", "myname", "mytag", "parent--myname--mytag"),
        ("", "myname", "mytag", "myname--mytag"),
    ],
    ids=[
        "only name",
        "parent and name",
        "parent, name and tagname",
        "name and tagname",
    ],
)
def test_regsurf_preprocessed_filename_retained(
    fmurun_prehook,
    rmssetup,
    rmsglobalconfig,
    regsurf,
    parent,
    name,
    tagname,
    exproot,
    monkeypatch,
):
    """
    Check that current name and/or tagname are propegated and
    retained when re-exporting preprocessed data.
    """

    @inside_rms
    def _export_data_from_rms(
        rmssetup,
        rmsglobalconfig,
        regsurf,
        parent,
        name,
        tagname,
        exproot,
    ):
        """Run an export of a preprocessed surface inside RMS."""
        logger.info("Active folder is %s", rmssetup)

        os.chdir(rmssetup)
        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            fmu_context="preprocessed",
            content="depth",
            parent=parent,
            timedata=[[20240802, "moni"], [20200909, "base"]],
            is_observation=True,
            name=name,
            tagname=tagname,
        )

        metadata = edata.generate_metadata(regsurf)

        dates = "20240802_20200909"
        assert (
            metadata["file"]["relative_path"]
            == f"share/preprocessed/maps/{exproot}--{dates}.gri"
        )

        return edata.export(regsurf)

    def _run_case_fmu(
        fmurun_prehook,
        rmsglobalconfig,
        surfacepath,
        exproot,
    ):
        """Run FMU workflow, using the preprocessed data on a subfolder."""

        os.chdir(fmurun_prehook)
        logger.info("Active folder is %s", fmurun_prehook)

        edata = dataio.ExportPreprocessedData(
            config=rmsglobalconfig,  # read from global config
            is_observation=True,
            casepath=fmurun_prehook,
        )
        prefix = "share/observations/maps"
        dates = "20240802_20200909"

        metadata = edata.generate_metadata(surfacepath)
        assert metadata["file"]["relative_path"] == f"{prefix}/{exproot}--{dates}.gri"

    remove_ert_env(monkeypatch)
    mysurf = _export_data_from_rms(
        rmssetup, rmsglobalconfig, regsurf, parent, name, tagname, exproot
    )
    set_ert_env_prehook(monkeypatch)
    _run_case_fmu(
        fmurun_prehook,
        rmsglobalconfig,
        mysurf,
        exproot,
    )


def test_regsurf_preprocessed_observation_subfolder(
    fmurun_prehook, rmssetup, rmsglobalconfig, regsurf, monkeypatch
):
    """As previous test, but with data using subfolder option.

    When the original output is using a subfolder key, the subsequent job shall detect
    this from the filepath and automatically output to the same subfolder name, also.

    Alternatively the subfolder can be given another name.
    """

    @inside_rms
    def _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf):
        """Run an export of a preprocessed surface inside RMS."""
        logger.info("Active folder is %s", rmssetup)

        os.chdir(rmssetup)
        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            fmu_context="preprocessed",
            name="preprocessedmap",
            content="depth",
            is_observation=True,
            timedata=[[20240802, "moni"], [20200909, "base"]],
            subfolder="mysub",
        )

        metadata = edata.generate_metadata(regsurf)
        logger.debug("\n%s", utils.prettyprint_dict(metadata))

        assert (
            metadata["file"]["relative_path"]
            == "share/preprocessed/maps/mysub/preprocessedmap--20240802_20200909.gri"
        )

        return edata.export(regsurf)

    def _run_case_fmu(fmurun_prehook, rmsglobalconfig, surfacepath):
        """Run FMU workflow, using the preprocessed data on a subfolder."""

        os.chdir(fmurun_prehook)
        logger.info("Active folder is %s", fmurun_prehook)

        edata = dataio.ExportPreprocessedData(
            config=rmsglobalconfig, casepath=fmurun_prehook, is_observation=True
        )
        metadata = edata.generate_metadata(surfacepath)
        # check that the relative path is identical to existing except the share folder
        assert (
            metadata["file"]["relative_path"]
            == "share/observations/maps/mysub/preprocessedmap--20240802_20200909.gri"
        )
        assert "merged" in metadata["tracklog"][-1]["event"]

    # run two stage process
    remove_ert_env(monkeypatch)
    mysurf = _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf)

    set_ert_env_prehook(monkeypatch)
    _run_case_fmu(fmurun_prehook, rmsglobalconfig, mysurf)


@inside_rms
def test_preprocessed_with_abs_forcefolder_shall_fail(
    rmssetup, rmsglobalconfig, regsurf
):
    """Run an export of a preprocessed surface inside RMS, with absolute forcefolder."""
    logger.info("Active folder is %s", rmssetup)

    os.chdir(rmssetup)
    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
        fmu_context="preprocessed",
        name="some",
        content="depth",
        is_observation=True,
        timedata=[[20240802, "moni"], [20200909, "base"]],
        forcefolder="/tmp",
    )

    with pytest.raises(ValueError, match="Can't use absolute path as 'forcefolder'"):
        edata.generate_metadata(regsurf)


@inside_rms
def test_preprocessed_with_rel_forcefolder_ok(rmssetup, rmsglobalconfig, regsurf):
    """Run an export of a preprocessed surface inside RMS, with forcefolder."""
    logger.info("Active folder is %s", rmssetup)

    os.chdir(rmssetup)
    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
        fmu_context="preprocessed",
        name="some",
        content="depth",
        is_observation=True,
        timedata=[[20240802, "moni"], [20200909, "base"]],
        forcefolder="tmp",
    )
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        meta = edata.generate_metadata(regsurf)

    assert "preprocessed/tmp" in meta["file"]["relative_path"]


def test_access_settings_retained(
    fmurun_prehook, rmssetup, rmsglobalconfig, regsurf, monkeypatch
):
    """Test that access level put on pre-processed data are retained when the
    metadata is being completed during later FMU run.

    The stub metadata is produced when data is made/pre-processed.
    When adding metadata during FMU runtime, the access shall be retained."""

    @inside_rms
    def _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf):
        """Run an export of a preprocessed surface inside RMS."""
        logger.info("Active folder is %s", rmssetup)

        # Confirm assumption: Access level in config is "internal"
        assert rmsglobalconfig["access"]["ssdl"]["access_level"] == "internal"

        os.chdir(rmssetup)
        edata = dataio.ExportData(
            config=rmsglobalconfig,
            fmu_context="preprocessed",
            name="preprocessedmap",
            content="depth",
            access_ssdl={"access_level": "restricted"},  # access != config
        )

        metadata = edata.generate_metadata(regsurf)
        logger.debug("\n%s", utils.prettyprint_dict(metadata))

        assert metadata["access"]["classification"] == "restricted"

        return edata.export(regsurf)

    def _run_case_fmu(fmurun_prehook, rmsglobalconfig, surfacepath):
        """Run FMU workflow, test that access is retained from preprocessed."""

        os.chdir(fmurun_prehook)
        logger.info("Active folder is %s", fmurun_prehook)

        edata = dataio.ExportPreprocessedData(
            config=rmsglobalconfig,
            casepath=fmurun_prehook,
        )
        metadata = edata.generate_metadata(surfacepath)

        # access shall be inherited from preprocessed data
        assert metadata["access"]["classification"] == "restricted"

    # run two stage process
    remove_ert_env(monkeypatch)
    surfacepath = _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf)
    set_ert_env_prehook(monkeypatch)
    _run_case_fmu(fmurun_prehook, rmsglobalconfig, surfacepath)
