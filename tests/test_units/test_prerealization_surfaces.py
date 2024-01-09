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
from pathlib import Path

import fmu.dataio.dataio as dataio
import pytest
from conftest import inside_rms
from fmu.dataio import _utils as utils

logger = logging.getLogger(__name__)


def test_regsurf_case_observation(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test generating pre-realization surfaces that comes right to case.

    Notice the difference between this use-case and the 'preprocessed' example later!
    """
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
        fmu_context="case",
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


def test_regsurf_case_observation_w_symlinks(
    fmurun_w_casemetadata, rmsglobalconfig, regsurf
):
    """Generating case level surface, with symlinks in realization folders."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
        fmu_context="case_symlink_realization",
        name="mymap",
        content="depth",
        is_observation=True,
    )
    metadata = edata.generate_metadata(regsurf)
    logger.info("\n%s", utils.prettyprint_dict(metadata))
    assert (
        "realization-0/iter-0/share/observations/maps/mymap.gri"
        in metadata["file"]["relative_path_symlink"]
    )

    exp = edata.export(regsurf, return_symlink=True)
    myfile = Path(exp)
    assert myfile.is_symlink() is True


def test_regsurf_preprocessed_observation(
    fmurun_w_casemetadata, rmssetup, rmsglobalconfig, regsurf
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
        logger.info("Active folder is %s", fmurun_w_casemetadata)

        casepath = fmurun_w_casemetadata.parent.parent

        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            fmu_context="case",
            content=None,  # shall be accepted without warning here in this context
            is_observation=True,
        )
        metadata = edata.generate_metadata(
            surfacepath,
            casepath=casepath,
        )
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

        # do the actual export (which will copy data to case/share/observations/...)
        edata.export(
            surfacepath,
            casepath=casepath,
        )
        assert (
            casepath
            / "share"
            / "observations"
            / "maps"
            / ".topvolantis--20240802_20200909.gri.yml"
        ).exists()

    # run two stage process
    mysurf = _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf)
    _run_case_fmu(fmurun_w_casemetadata, rmsglobalconfig, mysurf)

    logger.info("Preprocessed surface is %s", mysurf)


@pytest.mark.parametrize(
    "name_pre, tagname_pre, name_merge, tagname_merge, exproot1, exproot2",
    [
        ("myname", "", "", "", "myname", "myname"),
        ("myname", "", "newname", "", "myname", "newname"),
        ("myname", "mytag", "", "", "myname--mytag", "myname--mytag"),
        ("myname", "mytag", "newname", "newtag", "myname--mytag", "newname--newtag"),
        ("myname", "", "", "newtag", "myname", "myname--newtag"),
    ],
    ids=[
        "use both preprocessed name, no tagname",
        "change name, no tagname",
        "keep initial name and tagname",
        "change both name and tagname",
        "keep names, not initial tagname, but a merged tagname",
    ],
)
def test_regsurf_preprocessed_obs_vary_name_tagname(
    fmurun_w_casemetadata,
    rmssetup,
    rmsglobalconfig,
    regsurf,
    name_pre,
    tagname_pre,
    name_merge,
    tagname_merge,
    exproot1,
    exproot2,
):
    """Check that current name and/or tagname are propegated or updated."""

    @inside_rms
    def _export_data_from_rms(
        rmssetup,
        rmsglobalconfig,
        regsurf,
        name_pre,
        tagname_pre,
        exproot1,
    ):
        """Run an export of a preprocessed surface inside RMS."""
        logger.info("Active folder is %s", rmssetup)

        os.chdir(rmssetup)
        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            fmu_context="preprocessed",
            content="depth",
            timedata=[[20240802, "moni"], [20200909, "base"]],
            is_observation=True,
            name=name_pre,
            tagname=tagname_pre,
        )

        metadata = edata.generate_metadata(regsurf)

        dates = "20240802_20200909"
        assert (
            metadata["file"]["relative_path"]
            == f"share/preprocessed/maps/{exproot1}--{dates}.gri"
        )

        return edata.export(regsurf)

    def _run_case_fmu(
        fmurun_w_casemetadata,
        rmsglobalconfig,
        surfacepath,
        name_merge,
        tagname_merge,
        exproot2,
    ):
        """Run FMU workflow, using the preprocessed data on a subfolder."""

        os.chdir(fmurun_w_casemetadata)
        logger.info("Active folder is %s", fmurun_w_casemetadata)

        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            fmu_context="case",
            content="depth",
            is_observation=True,
            name=name_merge,
            tagname=tagname_merge,
        )
        prefix = "share/observations/maps"
        dates = "20240802_20200909"

        metadata = edata.generate_metadata(surfacepath)
        assert metadata["file"]["relative_path"] == f"{prefix}/{exproot2}--{dates}.gri"

    mysurf = _export_data_from_rms(
        rmssetup, rmsglobalconfig, regsurf, name_pre, tagname_pre, exproot1
    )
    _run_case_fmu(
        fmurun_w_casemetadata,
        rmsglobalconfig,
        mysurf,
        name_merge,
        tagname_merge,
        exproot2,
    )


def test_regsurf_preprocessed_observation_subfolder(
    fmurun_w_casemetadata, rmssetup, rmsglobalconfig, regsurf
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

    def _run_case_fmu(fmurun_w_casemetadata, rmsglobalconfig, surfacepath, subf=None):
        """Run FMU workflow, using the preprocessed data on a subfolder."""

        os.chdir(fmurun_w_casemetadata)
        logger.info("Active folder is %s", fmurun_w_casemetadata)

        edata = dataio.ExportData(
            config=rmsglobalconfig,  # read from global config
            fmu_context="case",
            content="depth",
            name="pre_v3",
            is_observation=True,
        )
        if subf is not None:
            metadata = edata.generate_metadata(surfacepath, subfolder=subf)
            assert (
                metadata["file"]["relative_path"]
                == f"share/observations/maps/{subf}/pre_v3--20240802_20200909.gri"
            )
        else:
            metadata = edata.generate_metadata(surfacepath)
            assert (
                metadata["file"]["relative_path"]
                == "share/observations/maps/mysub/pre_v3--20240802_20200909.gri"
            )
        assert "merged" in metadata["tracklog"][-1]["event"]

    # run two stage process
    mysurf = _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf)
    _run_case_fmu(fmurun_w_casemetadata, rmsglobalconfig, mysurf)
    _run_case_fmu(fmurun_w_casemetadata, rmsglobalconfig, mysurf, subf="xxxx")


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

    with pytest.raises(ValueError, match="Cannot use absolute path to 'forcefolder'"):
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
    fmurun_w_casemetadata, rmssetup, rmsglobalconfig, regsurf
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

    def _run_case_fmu(fmurun_w_casemetadata, rmsglobalconfig, surfacepath):
        """Run FMU workflow, test that access is retained from preprocessed."""

        os.chdir(fmurun_w_casemetadata)
        logger.info("Active folder is %s", fmurun_w_casemetadata)

        edata = dataio.ExportData(
            config=rmsglobalconfig,
            fmu_context="case",
            content="depth",
            name="MyName",
        )
        metadata = edata.generate_metadata(surfacepath)

        # access shall be inherited from preprocessed data
        assert metadata["access"]["classification"] == "restricted"

    # run two stage process
    surfacepath = _export_data_from_rms(rmssetup, rmsglobalconfig, regsurf)
    _run_case_fmu(fmurun_w_casemetadata, rmsglobalconfig, surfacepath)
