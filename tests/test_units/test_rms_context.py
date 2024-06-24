"""Test the dataio running from within RMS interactive as pretended context.

In this case a user sits in RMS, which is in folder rms/model and runs
interactive or from ERT. Hence the rootpath will be ../../
"""

import logging
import os
import shutil
from pathlib import Path

import fmu.dataio.dataio as dataio
import fmu.dataio.readers as readers
import pandas as pd
import pytest
import yaml
from fmu.dataio._utils import prettyprint_dict
from fmu.dataio.dataio import ValidationError

from ..utils import inside_rms

logger = logging.getLogger(__name__)

logger.info("Inside RMS status %s", dataio.ExportData._inside_rms)


@inside_rms
def test_regsurf_generate_metadata(rmssetup, rmsglobalconfig, regsurf):
    """Test generating metadata for a surface pretend inside RMS"""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    logger.debug(prettyprint_dict(rmsglobalconfig["access"]))

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",  # read from global config
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

    edata = dataio.ExportData(config=rmsglobalconfig, content="depth")
    meta1 = edata.generate_metadata(regsurf)

    edata = dataio.ExportData(config=rmsglobalconfig, content="time")
    meta2 = edata.generate_metadata(regsurf)

    assert meta1["data"]["content"] == "depth"
    assert meta2["data"]["content"] == "time"


@inside_rms
def test_regsurf_generate_metadata_change_content_invalid(rmsglobalconfig, regsurf):
    """As above but change an invalid name of key in the generate_metadata"""
    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth"
    )  # read from global config

    with pytest.raises(ValidationError):
        _ = edata.generate_metadata(regsurf, blablabla="time")


@inside_rms
def test_regsurf_export_file(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth"
    )  # read from global config

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

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="TopVolantis"
    )

    output = edata.export(regsurf)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/maps/topvolantis.gri").resolve()
    )

    meta = edata.generate_metadata(regsurf)
    assert meta["data"]["name"] == "VOLANTIS GP. Top"  # strat name from SMDA
    assert "TopVolantis" in meta["data"]["alias"]


@inside_rms
def test_regsurf_metadata_with_timedata(rmssetup, rmsglobalconfig, regsurf):
    """Export a regular surface to file with correct metadata and name and timedata."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        name="TopVolantis",
        timedata=[[20300101, "moni"], [20100203, "base"]],
    )
    meta1 = edata.generate_metadata(regsurf)
    assert meta1["data"]["time"]["t0"]["value"] == "2010-02-03T00:00:00"
    assert meta1["data"]["time"]["t0"]["label"] == "base"
    assert meta1["data"]["time"]["t1"]["value"] == "2030-01-01T00:00:00"
    assert meta1["data"]["time"]["t1"]["label"] == "moni"

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        name="TopVolantis",
        timedata=[[20300123, "one"]],
    )
    meta1 = edata.generate_metadata(regsurf)

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
    # should raise userwarning
    with pytest.warns(UserWarning, match="now deprecated"):
        edata = dataio.ExportData(
            config=rmsglobalconfig,
            content="depth",
            name="TopVolantis",
            timedata=[[20300101, "moni"], [20100203, "base"]],
        )

    meta1 = edata.generate_metadata(regsurf)

    assert "topvolantis--20300101_20100203" in meta1["file"]["relative_path"]

    # new format should be present in the metadata files
    assert meta1["data"]["time"]["t0"]["value"] == "2010-02-03T00:00:00"
    assert meta1["data"]["time"]["t0"]["label"] == "base"
    assert meta1["data"]["time"]["t1"]["value"] == "2030-01-01T00:00:00"
    assert meta1["data"]["time"]["t1"]["label"] == "moni"

    # check that metadata are equal independent of legacy_time_format
    dataio.ExportData.legacy_time_format = False
    meta2 = edata.generate_metadata(regsurf)
    assert meta2["data"]["time"] == meta1["data"]["time"]


@inside_rms
def test_regsurf_export_file_fmurun(
    rmsrun_fmu_w_casemetadata, rmsglobalconfig, regsurf
):
    """Being in RMS and in an active FMU ERT run with case metadata present.

    Export the regular surface to file with correct metadata and name.
    """

    logger.info("Active folder is %s", rmsrun_fmu_w_casemetadata)
    os.chdir(rmsrun_fmu_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        access_ssdl={"access_level": "restricted", "rep_include": False},
        content="depth",
        workflow="My test workflow",
        unit="myunit",
    )  # read from global config

    assert edata.unit == "myunit"

    # generating metadata without export is possible
    themeta = edata.generate_metadata(regsurf)
    assert themeta["data"]["unit"] == "myunit"
    logger.debug("Metadata: \n%s", prettyprint_dict(themeta))

    # doing actual export with a few ovverides
    with pytest.warns(FutureWarning, match="move them up to initialization"):
        output = edata.export(
            regsurf,
            name="TopVolantis",
            unit="forthnite",  # intentional override
        )
    logger.info("Output is %s", output)

    out = Path(edata.export(regsurf))
    with open(out.parent / f".{out.name}.yml", encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    assert metadata["access"]["ssdl"]["access_level"] == "restricted"
    assert metadata["data"]["unit"] == "forthnite"


# ======================================================================================
# Polygons and Points
# ======================================================================================


@inside_rms
def test_polys_export_file_set_name(rmssetup, rmsglobalconfig, polygons):
    """Export the polygon to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="TopVolantis"
    )

    output = edata.export(polygons)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/polygons/topvolantis.csv").resolve()
    )


@inside_rms
def test_points_export_file_set_name(rmssetup, rmsglobalconfig, points):
    """Export the points to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="TopVolantis"
    )

    output = edata.export(points)
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
        config=rmsglobalconfig, content="depth", name="TopVolantiz"
    )

    output = edata.export(points)
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

    edata = dataio.ExportData(config=rmsglobalconfig, content="depth", name="MyCube")

    output = edata.export(cube)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/cubes/mycube.segy").resolve()
    )


@inside_rms
def test_cube_export_file_set_name_as_observation(rmssetup, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata and name, is_observation."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", is_observation=True, name="MyCube"
    )

    output = edata.export(cube)
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

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        fmu_context="realization",
        is_observation=True,
        forcefolder="seismic",
        name="MyCube",
    )

    # use forcefolder to apply share/observations/seismic which trigger a warning
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        output = edata.export(cube)

    logger.info("Output after force is %s", output)
    assert str(output) == str(
        (edata._rootpath / "share/observations/seismic/mycube.segy").resolve()
    )


@inside_rms
def test_cube_export_as_case(rmssetup, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata and name, is_observation.

    In addition try fmu_context=case; when inside rms this should be reset to "non-fmu"
    """
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        fmu_context="case",
        is_observation=True,
        name="MyCube",
    )

    # use forcefolder to apply share/observations/seismic
    output = edata.export(cube)
    logger.info("Output %s", output)
    assert edata.fmu_context is None
    assert str(output) == str(
        (edata._rootpath / "share/observations/cubes/mycube.segy").resolve()
    )


@inside_rms
def test_case_symlink_realization_raises_error(rmssetup, rmsglobalconfig, monkeypatch):
    """Test that fmu_context="case_symlink_realization" raises error."""
    logger.info("Active folder is %s", rmssetup)
    monkeypatch.chdir(rmssetup)

    with pytest.raises(ValueError, match="no longer a supported option"):
        dataio.ExportData(
            config=rmsglobalconfig,
            content="depth",
            fmu_context="case_symlink_realization",
            is_observation=True,
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

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        is_observation=True,
        forcefolder="seismic/xxx",
        name="MyCube",
    )

    # use forcefolder to apply share/observations/seismic
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        output = edata.export(cube)
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

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        is_observation=True,
        forcefolder="seismic/xxx",
        subfolder="mysubfolder",
        name="MyCube",
    )

    # use forcefolder to apply share/observations/seismic
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        output = edata.export(cube)
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

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        is_observation=True,
        forcefolder="seismic/xxx",
        name="MyCube",
    )

    # use forcefolder to apply share/observations/seismic
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        output = edata.export(cube)
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

    edata = dataio.ExportData(config=rmsglobalconfig, content="depth", name="MyGrid")

    output = edata.export(grid)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/grids/mygrid.roff").resolve()
    )


@inside_rms
def test_gridproperty_export_file_set_name(rmssetup, rmsglobalconfig, gridproperty):
    """Export the gridprop to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="MyGridProperty"
    )

    output = edata.export(gridproperty)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/grids/mygridproperty.roff").resolve()
    )


@inside_rms
def test_gridproperty_export_with_geometry(
    rmssetup, rmsglobalconfig, grid, gridproperty
):
    """Export the the grid and the gridprop(s) with connected geometry."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    grd_edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="MyGrid"
    )
    grid_output = grd_edata.export(grid)

    # Here the export of the grid property point to the path of the exported geometry,
    # which is then sufficient to provide a geometry tag in the data settings.
    grdprop_edata = dataio.ExportData(
        config=rmsglobalconfig,
        content={"property": {"is_discrete": False}},
        name="MyProperty",
        geometry=grid_output,
    )
    output = grdprop_edata.export(gridproperty)

    assert "MyGrid".lower() in output  # grid name shall be a part of the name

    logger.info("Output is %s", output)
    metadata = dataio.read_metadata(output)

    assert metadata["data"]["geometry"]["name"] == "MyGrid"
    assert (
        metadata["data"]["geometry"]["relative_path"]
        == "share/results/grids/mygrid.roff"
    )

    # try with both parent and geometry, and geometry name shall win
    grdprop_edata_2 = dataio.ExportData(
        config=rmsglobalconfig,
        content={"property": {"is_discrete": False}},
        name="MyProperty",
        geometry=grid_output,
        parent="this_is_parent",
    )
    output = grdprop_edata_2.export(gridproperty)

    assert "mygrid" in output
    assert "this_is_parent" not in output

    # skip geometry; now parent name will present in name
    grdprop_edata_3 = dataio.ExportData(
        config=rmsglobalconfig,
        content={"property": {"is_discrete": False}},
        name="MyProperty",
        parent="this_is_parent",
    )
    output = grdprop_edata_3.export(gridproperty)

    assert "mygrid" not in output
    assert "this_is_parent" in output


# ======================================================================================
# Dataframe and PyArrow
# ======================================================================================


@inside_rms
def test_dataframe_export_file_set_name(rmssetup, rmsglobalconfig, dataframe):
    """Export the dataframe to file with correct metadata and name."""
    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="MyDataframe"
    )

    output = edata.export(dataframe)
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

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="MyArrowtable"
    )

    if arrowtable:  # is None if PyArrow package is not present
        output = edata.export(arrowtable)
        logger.info("Output is %s", output)

        assert str(output) == str(
            (edata._rootpath / "share/results/tables/myarrowtable.parquet").resolve()
        )

        metaout = dataio.read_metadata(output)
        assert metaout["data"]["spec"]["columns"] == ["COL1", "COL2"]


# ======================================================================================
# Faultroom data, for e.g. DynaGEO usage
# ======================================================================================


@inside_rms
def test_faultroom_export_as_file(rootpath, rmssetup, rmsglobalconfig):
    """Export the faultroom surfaces, use input as file"""

    # it assumes here that the faultroom plugin output file(s) to e.g.
    # ../output/faultroom, but here need some preps for this test
    f_room_files = (rootpath / "tests/data/drogon/rms/output/faultroom").glob("*.json")
    target_folder = rmssetup / ".." / "output" / "faultroom"
    target_folder.mkdir(parents=True, exist_ok=True)
    for file_ in f_room_files:
        shutil.copy(file_, target_folder)

    logger.info("Active folder is %s", rmssetup)
    os.chdir(rmssetup)

    # in RMS, the Faultroom plugin will export the results to a temporary folder, then
    # fmu-dataio will grab that, parse metadata and output to the 'right place'
    faultroom_files = Path("../output/faultroom").glob("*.json")

    for faultroom_file in faultroom_files:
        logger.info("Working with %s", faultroom_file)
        froom = readers.read_faultroom_file(faultroom_file)  # FaultRoomSurface instance
        output = dataio.ExportData(
            config=rmsglobalconfig, content="fault_properties", tagname=froom.tagname
        ).export(froom)
        logger.info("Output is %s", type(output))

        assert Path(output).name == "volantis_gp_top--faultroom_d1433e1.json"

        metaout = dataio.read_metadata(output)
        assert metaout["data"]["spec"]["faults"] == ["F1", "F2", "F3", "F4", "F5", "F6"]
