"""Test the main class DataExporter and functions in the dataio module, ExportData."""
import json
import logging
import re
import shutil
from collections import OrderedDict

import fmu.dataio
import pytest
import xtgeo
import yaml

# pylint: disable=protected-access

CFG = OrderedDict()
CFG["model"] = {"name": "Test", "revision": "21.0.0"}
CFG["masterdata"] = {
    "smda": {
        "country": [
            {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
        ],
        "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
    }
}
CFG["stratigraphy"] = {"TopVolantis": {}}
CFG["access"] = {"someaccess": "jail"}
CFG["model"] = {"revision": "0.99.0"}

RUN = "tests/data/drogon/ertrun1/realization-0/iter-0/rms"
RUNPATH = "tests/data/drogon/ertrun1/realization-0/iter-0"
#                             case      real        iter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def test_instantate_class_no_keys():
    """Test function _get_meta_master."""
    # it should be possible to parse without any key options
    case = fmu.dataio.ExportData()
    for attr, value in case.__dict__.items():
        print(attr, value)

    assert case._verbosity == "CRITICAL"
    assert case._is_prediction is True


def test_get_meta_dollars():
    """The private routine that provides special <names> (earlier with $ in front)."""
    case = fmu.dataio.ExportData()
    case._config = CFG
    logger.info(case._meta_dollars)
    assert "$schema" in case._meta_dollars
    assert "fmu" in case._meta_dollars["source"]


def test_get_meta_masterdata():
    """The private routine that provides masterdata."""
    case = fmu.dataio.ExportData()
    case._config = CFG
    case._get_meta_masterdata()
    assert case._meta_masterdata["smda"]["country"][0]["identifier"] == "Norway"


def test_get_meta_access():
    """The private routine that provides access."""
    case = fmu.dataio.ExportData()
    case._config = CFG
    case._get_meta_access()
    assert case._meta_access["someaccess"] == "jail"


def test_get_meta_tracklog():
    """The private routine that provides tracklog."""
    # placeholder


def test_process_fmu_model():
    """The (second order) private routine that provides fmu:model"""
    case = fmu.dataio.ExportData()
    case._config = CFG
    fmumodel = case._process_meta_fmu_model()
    assert fmumodel["revision"] == "0.99.0"


def test_get_folderlist():
    """Test the get_folderlist() helper function"""
    case = fmu.dataio.ExportData(verbosity="INFO", dryrun=True, runfolder=RUN)

    folderlist = case._get_folderlist()
    assert folderlist[-1] == "rms"
    assert folderlist[-2] == "iter-0"

    case2 = fmu.dataio.ExportData(verbosity="INFO", dryrun=True, runfolder=RUNPATH)
    folderlist = case2._get_folderlist()
    assert folderlist[-1] == "iter-0"
    assert folderlist[-2] == "realization-0"
    print(folderlist)


def test_process_fmu_realisation():
    """The (second order) private routine that provides realization and iteration."""
    case = fmu.dataio.ExportData(runfolder=RUN, verbosity="INFO", dryrun=True)
    case._config = CFG

    c_meta, i_meta, r_meta = case._process_meta_fmu_realization_iteration()
    logger.info("\nCASE\n%s", json.dumps(c_meta, indent=2, default=str))
    logger.info("\nITER\n%s", json.dumps(i_meta, indent=2, default=str))
    logger.info("\nREAL\n%s", json.dumps(r_meta, indent=2, default=str))

    assert r_meta["parameters"]["KVKH_CREVASSE"] == 0.3
    assert r_meta["parameters"]["GLOBVAR"]["VOLON_FLOODPLAIN_VOLFRAC"] == 0.256355
    assert c_meta["uuid"] == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"


def test_process_fmu_realisation_from_runpath():
    """The (second order) private routine that provides realization and iteration.

    Now running directly from RUNPATH.
    """
    case = fmu.dataio.ExportData(runfolder=RUNPATH, verbosity="INFO", dryrun=True)
    case._config = CFG

    c_meta, i_meta, r_meta = case._process_meta_fmu_realization_iteration()
    logger.info("\nCASE\n%s", json.dumps(c_meta, indent=2, default=str))
    logger.info("\nITER\n%s", json.dumps(i_meta, indent=2, default=str))
    logger.info("\nREAL\n%s", json.dumps(r_meta, indent=2, default=str))

    assert r_meta["parameters"]["KVKH_CREVASSE"] == 0.3
    assert r_meta["parameters"]["GLOBVAR"]["VOLON_FLOODPLAIN_VOLFRAC"] == 0.256355
    assert c_meta["uuid"] == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"


def test_raise_userwarning_missing_content(tmp_path):
    """Example on generating a GridProperty without content spesified."""

    gpr = xtgeo.GridProperty(ncol=10, nrow=11, nlay=12)
    gpr.name = "testgp"
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.grid_fformat = "roff"

    with pytest.warns(UserWarning, match="is not provided which defaults"):
        exp = fmu.dataio.ExportData(parent="unset", runfolder=tmp_path)
        exp.to_file(gpr)

    assert (tmp_path / "grids" / ".unset--testgp.roff.yml").is_file() is True


def test_exported_filenames(tmp_path):
    """Test that exported filenames are as expected"""

    fmu.dataio.ExportData.export_root = tmp_path.resolve()

    surf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=0, name="test"
    )

    # test case 1, vanilla
    exp = fmu.dataio.ExportData(
        name="myname",
        content="depth",
        runfolder=tmp_path,
    )

    exp.to_file(surf)
    assert (tmp_path / "maps" / "myname.gri").is_file() is True
    assert (tmp_path / "maps" / ".myname.gri.yml").is_file() is True

    # test case 2, dots in name
    exp = fmu.dataio.ExportData(
        name="myname.with.dots",
        content="depth",
        verbosity="DEBUG",
        runfolder=tmp_path,
    )
    # for a surface...
    exp.to_file(surf)
    assert (tmp_path / "maps" / "myname_with_dots.gri").is_file() is True
    assert (tmp_path / "maps" / ".myname_with_dots.gri.yml").is_file() is True

    # ...for a polygon...
    poly = xtgeo.Polygons()
    poly.from_list([(1.0, 2.0, 3.0, 0), (1.0, 2.0, 3.0, 0)])
    exp.to_file(poly)
    assert (tmp_path / "polygons" / "myname_with_dots.csv").is_file() is True
    assert (tmp_path / "polygons" / ".myname_with_dots.csv.yml").is_file() is True

    # ...and for a table.
    table = poly.dataframe
    exp.to_file(table)
    assert (tmp_path / "tables" / "myname_with_dots.csv").is_file() is True
    assert (tmp_path / "tables" / ".myname_with_dots.csv.yml").is_file() is True

    # ...for a grid property...
    exp = fmu.dataio.ExportData(
        name="myname",
        content="depth",
        parent="unset",
        runfolder=tmp_path,
    )

    gpr = xtgeo.GridProperty(ncol=10, nrow=11, nlay=12)
    gpr.name = "testgp"
    exp.to_file(gpr)
    assert (tmp_path / "grids" / "unset--myname.roff").is_file() is True
    assert (tmp_path / "grids" / ".unset--myname.roff.yml").is_file() is True


def test_file_block(tmp_path):
    """Test the content of the file metadata block"""

    # make it look like an ERT run
    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree("tests/data/drogon/ertrun1", current / "mycase")

    fmu.dataio.ExportData.export_root = "../../share/results"
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "maps"

    exp = fmu.dataio.ExportData(
        config=CFG,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="INFO",
        runfolder=runfolder.resolve(),
        workflow="my current workflow",
    )

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20,
        nrow=30,
        xinc=20,
        yinc=20,
        values=0,
        name="TopVolantis",
    )
    exp.to_file(srf, verbosity="INFO")

    metadataout = out / ".topvolantis--what_descr.gri.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream:
        meta = yaml.safe_load(stream)

    rel_path = meta["file"]["relative_path"]
    assert (
        rel_path
        == "realization-0/iter-0/share/results/maps/topvolantis--what_descr.gri"
    )

    abs_path = meta["file"]["absolute_path"]
    assert len(abs_path) > len(rel_path)
    assert abs_path.endswith(rel_path)

    # does not test validity, just that it looks right
    size_bytes = meta["file"]["size_bytes"]
    assert isinstance(size_bytes, int)

    # does not test validity, just that it looks right
    checksum_md5 = meta["file"]["checksum_md5"]
    assert re.match("^[a-z0-9]{32}", checksum_md5)
