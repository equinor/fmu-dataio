"""Test the dataio running from within RMS interactive as pretended context.

In this case a user sits in RMS, which is in folder rms/model and runs
interactive or from ERT. Hence the rootpath will be ../../
"""
import logging
import os

import pandas as pd
import pytest
from conftest import inside_rms

import fmu.dataio.dataio as dataio
from fmu.dataio._utils import prettyprint_dict
from fmu.dataio.dataio import ValidationError

logger = logging.getLogger(__name__)

logger.info("Inside RMS status %s", dataio.ExportData._inside_rms)


@inside_rms
def test_regsurf_generate_metadata(rmssetup, rmsglobalconfig, regsurf):
    """Test generating metadata for a surface pretend inside RMS"""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    logger.debug(prettyprint_dict(rmsglobalconfig["access"]))

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
    )
    logger.info("Inside RMS status now %s", dataio.ExportData._inside_rms)

    edata.generate_metadata(regsurf)
    assert str(edata._pwd) == str(rmssetup)
    assert str(edata._rootpath.resolve()) == str(rmssetup.parent.parent.resolve())


@inside_rms
def test_regsurf_generate_metadata_change_content(rmssetup, rmsglobalconfig, regsurf):
    """As above but change a key in the generate_metadata"""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    meta1 = edata.generate_metadata(regsurf)
    meta2 = edata.generate_metadata(regsurf, content="time")

    assert meta1["data"]["content"] == "depth"
    assert meta2["data"]["content"] == "time"


@inside_rms
def test_regsurf_generate_metadata_change_content_invalid(rmsglobalconfig, regsurf):
    """As above but change an invalid name of key in the generate_metadata"""
    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    with pytest.raises(ValidationError):
        _ = edata.generate_metadata(regsurf, blablabla="time")


@inside_rms
def test_regsurf_export_file(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(regsurf)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/maps/unknown.gri").resolve()
    )


@inside_rms
def test_regsurf_export_file_set_name(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(regsurf, name="TopVolantis")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/maps/topvolantis.gri").resolve()
    )


@inside_rms
def test_regsurf_metadata_with_timedata(rmssetup, rmsglobalconfig, regsurf):
    """Export a regular surface to file with correct metadata and name and timedata."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        verbosity="INFO",
    )  # read from global config
    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300101, "moni"], [20100203, "base"]],
        verbosity="INFO",
    )
    assert meta1["data"]["time"]["t0"]["value"] == "2010-02-03T00:00:00"
    assert meta1["data"]["time"]["t0"]["label"] == "base"
    assert meta1["data"]["time"]["t1"]["value"] == "2030-01-01T00:00:00"
    assert meta1["data"]["time"]["t1"]["label"] == "moni"

    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300123, "one"]],
        verbosity="INFO",
    )

    assert meta1["data"]["time"]["t0"]["value"] == "2030-01-23T00:00:00"
    assert meta1["data"]["time"]["t0"]["label"] == "one"
    assert meta1["data"]["time"].get("t1", None) is None

    logger.debug(prettyprint_dict(meta1))


@inside_rms
def test_regsurf_metadata_with_timedata_legacy(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata timedata, legacy ver."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    dataio.ExportData.legacy_time_format = True
    edata = dataio.ExportData(
        config=rmsglobalconfig,
        verbosity="INFO",
    )  # read from global config
    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300101, "moni"], [20100203, "base"]],
        verbosity="INFO",
    )
    logger.debug(prettyprint_dict(meta1))
    assert "topvolantis--20300101_20100203" in meta1["file"]["relative_path"]

    assert meta1["data"]["time"][0]["value"] == "2010-02-03T00:00:00"
    assert meta1["data"]["time"][0]["label"] == "base"
    assert meta1["data"]["time"][1]["value"] == "2030-01-01T00:00:00"
    assert meta1["data"]["time"][1]["label"] == "moni"

    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300123, "one"]],
        verbosity="INFO",
    )

    logger.debug(prettyprint_dict(meta1))

    assert meta1["data"]["time"][0]["value"] == "2030-01-23T00:00:00"
    assert meta1["data"]["time"][0]["label"] == "one"

    assert len(meta1["data"]["time"]) == 1

    dataio.ExportData.legacy_time_format = False


@inside_rms
def test_regsurf_export_file_fmurun(
    rmsrun_fmu_w_casemetadata, rmsglobalconfig, regsurf
):
    """Being in RMS and in an active FMU ERT2 run with case metadata present.

    Export the regular surface to file with correct metadata and name.
    """

    logger.info("Active folder is %s", rmsrun_fmu_w_casemetadata)
    os.chdir(rmsrun_fmu_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        verbosity="INFO",
        workflow="My test workflow",
        unit="myunit",
    )  # read from global config

    assert edata.unit == "myunit"

    # generating metadata without export is possible
    themeta = edata.generate_metadata(
        regsurf,
        unit="furlongs",  # intentional override
    )
    assert themeta["data"]["unit"] == "furlongs"
    logger.debug("Metadata: \n%s", prettyprint_dict(themeta))

    # doing actual export with a few ovverides
    output = edata.export(
        regsurf,
        name="TopVolantis",
        access_ssdl={"access_level": "restricted", "rep_include": False},
        unit="forthnite",  # intentional override
    )
    logger.info("Output is %s", output)

    assert edata._metadata["access"]["ssdl"]["access_level"] == "restricted"
    assert edata._metadata["data"]["unit"] == "forthnite"


# ======================================================================================
# Polygons and Points
# ======================================================================================


@inside_rms
def test_polys_export_file_set_name(rmssetup, rmsglobalconfig, polygons):
    """Export the polygon to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(polygons, name="TopVolantis")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/polygons/topvolantis.csv").resolve()
    )


@inside_rms
def test_points_export_file_set_name(rmssetup, rmsglobalconfig, points):
    """Export the points to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(points, name="TopVolantis")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/points/topvolantis.csv").resolve()
    )

    thefile = pd.read_csv(edata._rootpath / "share/results/points/topvolantis.csv")
    assert thefile.columns[0] == "X"


@inside_rms
def test_points_export_file_set_name_xtgeoheaders(rmssetup, rmsglobalconfig, points):
    """Export the points to file with correct metadata and name but here xtgeo var."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    dataio.ExportData.points_fformat = "csv|xtgeo"

    edata = dataio.ExportData(
        config=rmsglobalconfig, verbosity="INFO"
    )  # read from global config

    output = edata.export(points, name="TopVolantiz")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/points/topvolantiz.csv").resolve()
    )

    thefile = pd.read_csv(edata._rootpath / "share/results/points/topvolantiz.csv")
    assert thefile.columns[0] == "X_UTME"

    dataio.ExportData.points_fformat = "csv"


# ======================================================================================
# Cube
# This is also used to test various configurations of "forcefolder" and "fmu_context"
# ======================================================================================


@inside_rms
def test_cube_export_file_set_name(rmssetup, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(cube, name="MyCube")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/cubes/mycube.segy").resolve()
    )


@inside_rms
def test_cube_export_file_set_name_as_observation(rmssetup, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata and name, is_observation."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(cube, name="MyCube", is_observation=True)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/observations/cubes/mycube.segy").resolve()
    )


@inside_rms
def test_cube_export_file_set_name_as_observation_forcefolder(
    rmssetup, rmsglobalconfig, cube
):
    """Export the cube to file with correct metadata and name, is_observation.

    In addition, use forcefolder to apply "seismic" instead of cube
    """
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    # use forcefolder to apply share/observations/seismic which trigger a warning
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        output = edata.export(
            cube,
            name="MyCube",
            fmu_context="realization",
            is_observation=True,
            forcefolder="seismic",
        )

    logger.info("Output after force is %s", output)
    assert str(output) == str(
        (edata._rootpath / "share/observations/seismic/mycube.segy").resolve()
    )


@inside_rms
def test_cube_export_as_case(rmssetup, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata and name, is_observation.

    In addition, try fmu_conext=case
    """
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    # use forcefolder to apply share/observations/seismic
    output = edata.export(
        cube,
        name="MyCube",
        fmu_context="case",
        is_observation=True,
    )
    logger.info("Output %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/observations/cubes/mycube.segy").resolve()
    )


@inside_rms
def test_cube_export_as_case_symlink_realization(rmssetup, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata and name, is_observation.

    In addition, try fmu_conext=case
    """
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(
        cube,
        name="MyCube",
        fmu_context="case_symlink_realization",
        is_observation=True,
    )
    logger.info("Output %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/observations/cubes/mycube.segy").resolve()
    )


@inside_rms
def test_cube_export_as_observation_forcefolder_w_added_folder(
    rmssetup, rmsglobalconfig, cube
):
    """Export the cube to file with correct metadata and name, is_observation.

    In addition, use forcefolder with extra folder "xxx" (alternative to 'subfolder'
    key).
    """
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    # use forcefolder to apply share/observations/seismic
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        output = edata.export(
            cube,
            name="MyCube",
            is_observation=True,
            forcefolder="seismic/xxx",
        )
    logger.info("Output after force is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/observations/seismic/xxx/mycube.segy").resolve()
    )


@inside_rms
def test_cube_export_as_observation_forcefolder_w_true_subfolder(
    rmssetup, rmsglobalconfig, cube
):
    """Export the cube to file with correct metadata and name, is_observation.

    In addition, use forcefolder and subfolders in combination.
    """
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    # use forcefolder to apply share/observations/seismic
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        output = edata.export(
            cube,
            name="MyCube",
            is_observation=True,
            forcefolder="seismic/xxx",
            subfolder="mysubfolder",
        )
    logger.info("Output after force is %s", output)

    assert str(output) == str(
        (
            edata._rootpath / "share/observations/seismic/xxx/mysubfolder/mycube.segy"
        ).resolve()
    )


@inside_rms
def test_cube_export_as_observation_forcefolder_w_subfolder_case(
    rmssetup, rmsglobalconfig, cube
):
    """Export the cube to file with correct metadata and name, is_observation.

    In addition, use forcefolder with subfolders to apply "seismic" instead of cube
    and the fmu_context here is case, not realization.

    When inside RMS interactive, the case may be unresolved and hence the folder
    shall be as is.
    """
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    # use forcefolder to apply share/observations/seismic
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        output = edata.export(
            cube,
            name="MyCube",
            is_observation=True,
            fmu_context="case",
            forcefolder="seismic/xxx",
        )
    logger.info("Output after force is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/observations/seismic/xxx/mycube.segy").resolve()
    )


# ======================================================================================
# Grid and GridProperty
# ======================================================================================


@inside_rms
def test_grid_export_file_set_name(rmssetup, rmsglobalconfig, grid):
    """Export the grid to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(grid, name="MyGrid")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/grids/mygrid.roff").resolve()
    )


@inside_rms
def test_gridproperty_export_file_set_name(rmssetup, rmsglobalconfig, gridproperty):
    """Export the gridprop to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(gridproperty, name="MyGridProperty")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/grids/mygridproperty.roff").resolve()
    )


# ======================================================================================
# Dataframe and PyArrow
# ======================================================================================


@inside_rms
def test_dataframe_export_file_set_name(rmssetup, rmsglobalconfig, dataframe):
    """Export the dataframe to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(dataframe, name="MyDataframe")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/tables/mydataframe.csv").resolve()
    )

    metaout = dataio.read_metadata(output)
    assert metaout["data"]["spec"]["columns"] == ["COL1", "COL2"]


@inside_rms
def test_pyarrow_export_file_set_name(rmssetup, rmsglobalconfig, arrowtable):
    """Export the arrow to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    if arrowtable:  # is None if PyArrow package is not present
        output = edata.export(arrowtable, name="MyArrowtable")
        logger.info("Output is %s", output)

        assert str(output) == str(
            (edata._rootpath / "share/results/tables/myarrowtable.arrow").resolve()
        )

        metaout = dataio.read_metadata(output)
        assert metaout["data"]["spec"]["columns"] == ["COL1", "COL2"]
