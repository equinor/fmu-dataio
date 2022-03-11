"""Test the main class DataExporter and functions in the dataio module, ExportData."""
import json
import logging
import os
import re
import shutil
from collections import OrderedDict
from copy import deepcopy

import pytest
import xtgeo
import yaml

import fmu.dataio

# pylint: disable=protected-access, no-member

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
CFG["access"] = {
    "asset": "Drogon",
    "ssdl": {"access_level": "internal", "some_access_tag": True},
}
CFG["model"] = {"revision": "0.99.0"}

RUN = "tests/data/drogon/ertrun1/realization-0/iter-0/rms"
RUNPATH = "tests/data/drogon/ertrun1/realization-0/iter-0"
#                             case      real        iter

GLOBAL_CONFIG = "tests/data/drogon/global_config2/global_variables.yml"
GLOBAL_CONFIG_INVALID = "tests/data/drogon/global_config2/not_valid_yaml.yml"

FMUP1 = "share/results"


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def test_instantate_class_no_keys():
    """Test function _get_meta_master."""
    # it should be possible to parse without any key options except config
    case = fmu.dataio.ExportData(config=CFG)
    for attr, value in case.__dict__.items():
        print(attr, value)

    assert case._verbosity == "CRITICAL"
    assert case._is_prediction is True


def test_get_meta_dollars():
    """The private routine that provides special <names> (earlier with $ in front)."""
    case = fmu.dataio.ExportData(config=CFG)
    logger.info(case.metadata4dollars)
    assert "$schema" in case.metadata4dollars
    assert "fmu" in case.metadata4dollars["source"]


def test_get_meta_masterdata():
    """The private routine that provides masterdata."""
    case = fmu.dataio.ExportData(config=CFG)
    case._get_meta_masterdata()
    assert case.metadata4masterdata["smda"]["country"][0]["identifier"] == "Norway"


def test_get_meta_access():
    """The private routine that provides access."""

    # access_ssdl is not given, ssdl is kept as-is from config
    case = fmu.dataio.ExportData(config=CFG)
    case._get_meta_access()
    assert case.metadata4access["asset"] == "Drogon"
    assert case.metadata4access["ssdl"] == {
        "access_level": "internal",  # default
        "some_access_tag": True,  # default
    }

    # both access_ssdl tags in config are given and overwritten
    case = fmu.dataio.ExportData(
        access_ssdl={"access_level": "asset", "some_access_tag": False}, config=CFG
    )
    case._get_meta_access()
    assert case.metadata4access["asset"] == "Drogon"
    assert case.metadata4access["ssdl"] == {
        "access_level": "asset",  # input
        "some_access_tag": False,  # input
    }

    # only ssdl.access_level is given to overwrite from config
    case = fmu.dataio.ExportData(config=CFG, access_ssdl={"access_level": "asset"})
    case._get_meta_access()
    assert case.metadata4access["asset"] == "Drogon"
    assert case.metadata4access["ssdl"] == {
        "access_level": "asset",  # input
        "some_access_tag": True,  # default
    }

    # only ssdl.some_access_tag is given to overwrite from config
    case = fmu.dataio.ExportData(config=CFG, access_ssdl={"some_access_tag": False})
    case._get_meta_access()
    assert case.metadata4access["asset"] == "Drogon"
    assert case.metadata4access["ssdl"] == {
        "access_level": "internal",  # default
        "some_access_tag": False,  # input
    }

    # asset is not present in config, shall raise
    case = fmu.dataio.ExportData(config=CFG, access_ssdl={"some_access_tag": False})
    _tmp_cfg = deepcopy(CFG)
    del _tmp_cfg["access"]["asset"]
    case._config = _tmp_cfg
    with pytest.raises(ValueError):
        case._get_meta_access()

    # access_ssdl is not given as a dict
    with pytest.raises(TypeError):
        case = fmu.dataio.ExportData(access_ssdl="somestring", config=CFG)


def test_get_meta_tracklog():
    """The private routine that provides tracklog."""
    # placeholder


def test_process_fmu_workflow():
    """The (second order) routine that processes fmu.workflow"""

    case = fmu.dataio.ExportData(config=CFG)

    # If string is given, it shall be put into the reference sublevel
    case._workflow = "my workflow 1"
    case._process_meta_fmu_workflow()
    assert case.metadata4fmu["workflow"] == {"reference": "my workflow 1"}

    # If dict is given, it shall contain the reference sublevel, and be used directly
    case._workflow = {"reference": "my workflow 2"}
    case._process_meta_fmu_workflow()
    assert case.metadata4fmu["workflow"] == {"reference": "my workflow 2"}

    # workflow dict shall contain the "reference" key
    case._workflow = {"wrong": "my workflow 3"}
    with pytest.raises(ValueError):
        case._process_meta_fmu_workflow()

    # workflow shall be str or dict
    case._workflow = 1.0
    with pytest.raises(ValueError):
        case._process_meta_fmu_workflow()


def test_process_fmu_model():
    """The (second order) private routine that provides fmu:model"""
    case = fmu.dataio.ExportData(config=CFG)
    fmumodel = case._process_meta_fmu_model()
    assert fmumodel["revision"] == "0.99.0"


def test_get_folderlist():
    """Test the get_folderlist() helper function"""
    case = fmu.dataio.ExportData(
        verbosity="INFO", dryrun=True, runfolder=RUN, config=CFG
    )

    folderlist = case._get_folderlist()
    assert folderlist[-1] == "rms"
    assert folderlist[-2] == "iter-0"

    case2 = fmu.dataio.ExportData(
        verbosity="INFO", dryrun=True, runfolder=RUNPATH, config=CFG
    )
    folderlist = case2._get_folderlist()
    assert folderlist[-1] == "iter-0"
    assert folderlist[-2] == "realization-0"


def test_process_config():
    """Test raise when no config provided"""
    with pytest.raises(ValueError):
        fmu.dataio.ExportData(config=None)


def test_validate_config():
    """Test raise when missing required config keys"""
    _tmp_cfg = deepcopy(CFG)
    del _tmp_cfg["model"]
    with pytest.raises(ValueError):
        fmu.dataio.ExportData(config=_tmp_cfg)


def test_process_fmu_config_from_env():
    """Apply config from the env variabel FMU_GLOBAL_CONFIG"""
    os.environ["FMU_GLOBAL_CONFIG"] = GLOBAL_CONFIG

    edata = fmu.dataio.ExportData(
        config=None, runfolder=RUN, verbosity="INFO", dryrun=True
    )
    assert (
        edata._config["masterdata"]["smda"]["coordinate_system"]["identifier"]
        == "ST_WGS84_UTM37N_P32637"
    )


def test_process_fmu_config_from_env_fail():
    """Apply config from the env variabel FMU_GLOBAL_CONFIG"""
    os.environ["FMU_GLOBAL_CONFIG"] = "non_existing_file"

    with pytest.raises(FileNotFoundError):
        _ = fmu.dataio.ExportData(
            config=None, runfolder=RUN, verbosity="INFO", dryrun=True
        )
    del os.environ["FMU_GLOBAL_CONFIG"]


def test_process_fmu_config_from_env_invalid_yaml():
    """Apply config from the env variabel FMU_GLOBAL_CONFIG but the file is not YAML."""
    os.environ["FMU_GLOBAL_CONFIG"] = GLOBAL_CONFIG_INVALID

    with pytest.raises(yaml.YAMLError):
        _ = fmu.dataio.ExportData(
            config=None, runfolder=RUN, verbosity="INFO", dryrun=True
        )

    del os.environ["FMU_GLOBAL_CONFIG"]


def test_parse_scratch_folder_structure():
    """The private routine that parses the folder structure and derives information"""
    case = fmu.dataio.ExportData(
        runfolder=RUN, verbosity="INFO", dryrun=True, config=CFG
    )
    case._parse_scratch_folder_structure()
    assert str(case._casepath).endswith("drogon/ertrun1")
    assert str(case._realpath).endswith("drogon/ertrun1/realization-0")
    assert str(case._iterpath).endswith("drogon/ertrun1/realization-0/iter-0")

    assert case._realization_id == 0
    assert case._iteration_id == 0

    assert case._realname == "realization-0"
    assert case._itername == "iter-0"


def test_get_ert_information():
    """Test the private routine for getting ert information"""
    case = fmu.dataio.ExportData(
        runfolder=RUN, verbosity="INFO", dryrun=True, config=CFG
    )

    case._parse_scratch_folder_structure()
    case._get_ert_information()

    assert isinstance(case._ert["params"], dict)
    assert isinstance(case._ert["jobs"], dict)


def test_process_fmu_case():
    """Test the private routine that provides case"""
    case = fmu.dataio.ExportData(
        runfolder=RUN, verbosity="INFO", dryrun=True, config=CFG
    )

    case._parse_scratch_folder_structure()
    case._get_ert_information()
    c_meta = case._process_meta_fmu_case()

    assert c_meta["uuid"] == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"


def test_process_fmu_realization():
    """The (second order) private routine that provides realization"""
    case = fmu.dataio.ExportData(
        runfolder=RUN, verbosity="INFO", dryrun=True, config=CFG
    )

    case._parse_scratch_folder_structure()
    case._get_ert_information()
    c_meta = case._process_meta_fmu_case()
    case._case_uuid = c_meta["uuid"]
    r_meta = case._process_meta_fmu_realization()
    # logger.info("\nCASE\n%s", json.dumps(c_meta, indent=2, default=str))
    # logger.info("\nITER\n%s", json.dumps(i_meta, indent=2, default=str))
    logger.info("\nREAL\n%s", json.dumps(r_meta, indent=2, default=str))

    assert r_meta["parameters"]["KVKH_CREVASSE"] == 0.3
    assert r_meta["parameters"]["GLOBVAR"]["VOLON_FLOODPLAIN_VOLFRAC"] == 0.256355


def test_process_fmu_realization_from_runpath():
    """The (second order) private routine that provides realization and iteration.

    Now running directly from RUNPATH.
    """
    case = fmu.dataio.ExportData(
        runfolder=RUNPATH, verbosity="INFO", dryrun=True, config=CFG
    )

    case._parse_scratch_folder_structure()
    case._get_ert_information()
    c_meta = case._process_meta_fmu_case()
    case._case_uuid = c_meta["uuid"]
    r_meta = case._process_meta_fmu_realization()
    # logger.info("\nCASE\n%s", json.dumps(c_meta, indent=2, default=str))
    # logger.info("\nITER\n%s", json.dumps(i_meta, indent=2, default=str))
    logger.info("\nREAL\n%s", json.dumps(r_meta, indent=2, default=str))

    assert r_meta["parameters"]["KVKH_CREVASSE"] == 0.3
    assert r_meta["parameters"]["GLOBVAR"]["VOLON_FLOODPLAIN_VOLFRAC"] == 0.256355


def test_process_fmu_iteration():
    """The (second order) private routine that provides iteration"""
    case = fmu.dataio.ExportData(
        runfolder=RUN, verbosity="INFO", dryrun=True, config=CFG
    )
    case._parse_scratch_folder_structure()
    case._get_ert_information()
    c_meta = case._process_meta_fmu_case()
    case._case_uuid = c_meta["uuid"]
    i_meta = case._process_meta_fmu_iteration()

    assert i_meta["id"] == 0
    assert i_meta["name"] == "iter-0"
    assert i_meta["runid"] == "26295:22197:2021-4-20-12-50-55:406759315d"


def test_raise_userwarning_missing_content(tmp_path):
    """Example on generating a GridProperty without content spesified."""

    gpr = xtgeo.GridProperty(ncol=10, nrow=11, nlay=12)
    gpr.name = "testgp"
    fmu.dataio.ExportData.grid_fformat = "roff"

    with pytest.warns(UserWarning, match="is not provided which defaults"):
        exp = fmu.dataio.ExportData(parent="unset", runpath=tmp_path, config=CFG)
        exp.export(gpr)

    assert (tmp_path / FMUP1 / "grids" / ".unset--testgp.roff.yml").is_file() is True


def test_exported_filenames(tmp_path):
    """Test that exported filenames are as expected"""

    surf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=0, name="test"
    )

    # test case 1, vanilla
    exp = fmu.dataio.ExportData(
        name="myname",
        content="depth",
        runpath=tmp_path,
        config=CFG,
    )

    exp.export(surf)
    assert (tmp_path / FMUP1 / "maps" / "myname.gri").is_file() is True
    assert (tmp_path / FMUP1 / "maps" / ".myname.gri.yml").is_file() is True

    # test case 2, dots in name
    exp = fmu.dataio.ExportData(
        name="myname.with.dots",
        content="depth",
        verbosity="DEBUG",
        runpath=tmp_path,
        config=CFG,
    )
    # for a surface...
    exp.export(surf)
    assert (tmp_path / FMUP1 / "maps" / "myname_with_dots.gri").is_file() is True
    assert (tmp_path / FMUP1 / "maps" / ".myname_with_dots.gri.yml").is_file() is True

    # ...for a polygon...
    poly = xtgeo.Polygons([(1.0, 2.0, 3.0, 0), (1.0, 2.0, 3.0, 0)])
    exp.export(poly)
    assert (tmp_path / FMUP1 / "polygons" / "myname_with_dots.csv").is_file() is True
    assert (
        tmp_path / FMUP1 / "polygons" / ".myname_with_dots.csv.yml"
    ).is_file() is True

    # ...for a points object...
    poi = xtgeo.Points([(1.0, 2.0, 3.0), (1.0, 2.0, 3.0)])

    exp.export(poi)
    assert (tmp_path / FMUP1 / "points" / "myname_with_dots.csv").is_file() is True
    assert (tmp_path / FMUP1 / "points" / ".myname_with_dots.csv.yml").is_file() is True

    # ...and for a table.
    table = poly.dataframe
    exp.export(table)
    assert (tmp_path / FMUP1 / "tables" / "myname_with_dots.csv").is_file() is True
    assert (tmp_path / FMUP1 / "tables" / ".myname_with_dots.csv.yml").is_file() is True

    # ...for a grid property...
    exp = fmu.dataio.ExportData(
        name="myname",
        content="depth",
        parent="unset",
        runpath=tmp_path,
        config=CFG,
    )

    gpr = xtgeo.GridProperty(ncol=10, nrow=11, nlay=12)
    gpr.name = "testgp"
    exp.export(gpr)
    assert (tmp_path / FMUP1 / "grids" / "unset--myname.roff").is_file() is True
    assert (tmp_path / FMUP1 / "grids" / ".unset--myname.roff.yml").is_file() is True


def test_file_block(tmp_path):
    """Test the content of the file metadata block"""

    # make it look like an ERT run
    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree("tests/data/drogon/ertrun1", current / "mycase")

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
        inside_rms=True,  # pretend to be inside RMS since runfolder is at rms model
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
    assert exp.export(srf, verbosity="INFO") == str(out / "topvolantis--what_descr.gri")

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


def test_fmu_block(tmp_path):
    """Test the content of the fmu metadata block"""

    # make it look like an ERT run
    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree("tests/data/drogon/ertrun1", current / "mycase")

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
        inside_rms=True,  # pretend to be inside RMS since runfolder is at rms model
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
    assert exp.export(srf, verbosity="INFO") == str(out / "topvolantis--what_descr.gri")

    metadataout = out / ".topvolantis--what_descr.gri.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream:
        meta = yaml.safe_load(stream)

    # workflow shall be a dictionary
    assert isinstance(meta["fmu"]["workflow"], dict)
    assert meta["fmu"]["workflow"]["reference"] == "my current workflow"

    assert meta["fmu"]["model"]["revision"] == "0.99.0"
    # assert meta["fmu"]["model"]["name"] == "ff"  # TODO

    assert meta["fmu"]["case"]["name"] == "somecasename"
    assert meta["fmu"]["case"]["uuid"] == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"

    assert isinstance(meta["fmu"]["case"]["user"], dict)
    assert "id" in meta["fmu"]["case"]["user"]


def test_access_block(tmp_path):
    """Test the content of the access block"""

    # make it look like an ERT run
    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree("tests/data/drogon/ertrun1", current / "mycase")

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
        inside_rms=True,  # pretend to be inside RMS since runfolder is at rms model
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
    assert exp.export(srf, verbosity="INFO") == str(out / "topvolantis--what_descr.gri")

    metadataout = out / ".topvolantis--what_descr.gri.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream:
        meta = yaml.safe_load(stream)

    # access shall be a dictionary and shall contain keys 'asset' and 'ssdl'
    assert isinstance(meta["access"], dict)
    assert "asset" in meta["access"]
    assert "ssdl" in meta["access"]

    # access.ssdl shall be present and be a dictionary
    assert isinstance(meta["access"]["ssdl"], dict)

    # if not explicitly given, default shall be used
    assert meta["access"] == {
        "asset": "Drogon",
        "ssdl": {"access_level": "internal", "some_access_tag": True},
    }

    # if explicitly given, defaults shall be overrided for those fields given
    fmu.dataio.ExportData(
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
        access={"asset": "Drogon"},
    ).export(srf, verbosity="INFO")

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream:
        meta = yaml.safe_load(stream)

    assert meta["access"] == {
        "asset": "Drogon",
        "ssdl": {"access_level": "internal", "some_access_tag": True},
    }


def test_data_block(tmp_path):
    """Test the content of the data metadata block"""

    # make it look like an ERT run
    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree("tests/data/drogon/ertrun1", current / "mycase")

    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "maps"

    with open(GLOBAL_CONFIG, "r") as stream:
        _config = yaml.safe_load(stream)

    exp = fmu.dataio.ExportData(
        config=_config,
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
        description="Some description",
        inside_rms=True,  # pretend to be inside RMS since runfolder is at rms model
    )

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20,
        nrow=30,
        xinc=1,
        yinc=1,
        values=0,
        name="TopVolantis",
    )
    assert exp.export(srf, verbosity="INFO") == str(out / "topvolantis--what_descr.gri")

    metadataout = out / ".topvolantis--what_descr.gri.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream:
        meta = yaml.safe_load(stream)

    assert meta["data"]["stratigraphic"] is True
    assert meta["data"]["name"] == "VOLANTIS GP. Top"
    assert meta["data"]["content"] == "depth"
    assert meta["data"]["vertical_domain"] == "depth"
    assert meta["data"]["depth_reference"] == "msl"
    assert meta["data"]["is_prediction"] is True
    assert meta["data"]["is_observation"] is False
    assert meta["data"]["layout"] == "regular"
    assert meta["data"]["description"] == ["Some description"]

    assert isinstance(meta["data"]["spec"], dict)
    assert isinstance(meta["data"]["bbox"], dict)

    assert meta["data"]["format"] == "irap_binary"
