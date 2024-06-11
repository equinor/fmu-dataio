"""Test the dataio re-export of preprocessed data through ExportDataPreprocessed."""

import logging
from pathlib import Path

import fmu.dataio as dataio
import pytest
import yaml
from fmu.dataio import _utils as utils
from fmu.dataio.exceptions import InvalidMetadataError
from fmu.dataio.providers._fmu import ERT_RELATIVE_CASE_METADATA_FILE

from ..conftest import remove_ert_env, set_ert_env_forward, set_ert_env_prehook

logger = logging.getLogger(__name__)

PREPROCESSED_SURFACEPATH = (
    "share/preprocessed/maps/mysubfolder/topvolantis--20240802_20200909.gri"
)


def read_metadata(objmetafile):
    with open(objmetafile, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def export_preprocessed_surface(config, regsurf):
    edata = dataio.ExportData(
        config=config,
        fmu_context="preprocessed",
        name="TopVolantis",
        content="depth",
        timedata=[[20240802, "moni"], [20200909, "base"]],
        subfolder="mysubfolder",
    )
    surfacepath = Path(edata.export(regsurf))
    metafile = surfacepath.parent / f".{surfacepath.name}.yml"
    return surfacepath, metafile


def test_export_preprocessed_surfacefile(
    fmurun_prehook, rmsglobalconfig, regsurf, monkeypatch
):
    """
    Test re-exporting a preprocessed surface in a fmu run, and check that the
    existing metadata is updated with fmu/file/tracklog information and
    the _preprocessed flag is removed.
    """
    # mock being outside of FMU and export preprocessed surface
    remove_ert_env(monkeypatch)
    surfacepath, metafile = export_preprocessed_surface(rmsglobalconfig, regsurf)

    existing_meta = read_metadata(metafile)
    # check that '_preprocesssed' is originally present
    assert "_preprocessed" in existing_meta

    # run the re-export of the preprocessed data inside an mocked FMU run
    set_ert_env_prehook(monkeypatch)
    edata = dataio.ExportPreprocessedData(
        config=rmsglobalconfig, is_observation=True, casepath=fmurun_prehook
    )
    # generate the updated metadata
    metadata = edata.generate_metadata(surfacepath)

    # check that _preprocessed is removed
    assert "_preprocessed" not in metadata

    # check that the fmu block is added
    assert "fmu" in metadata
    assert metadata["fmu"]["context"]["stage"] == "case"
    assert "realization" not in metadata["fmu"]

    # check that the file paths are updated. The relative_path should be
    # equal to the initial export except for the share folder
    relative_path = PREPROCESSED_SURFACEPATH.replace("preprocessed", "observations")
    absolute_path = fmurun_prehook / relative_path
    assert metadata["file"]["relative_path"] == relative_path
    assert metadata["file"]["absolute_path"] == str(absolute_path)

    # check that the tracklog contains two events and the last is a "merged" event
    assert len(metadata["tracklog"]) == 2
    assert "merged" in metadata["tracklog"][-1]["event"]

    #  check that for all other keys the new metadata is equal to the existing
    for key, value in existing_meta.items():
        if key not in ["fmu", "file", "tracklog", "_preprocessed"]:
            assert metadata[key] == value

    # do the actual export and check that both files exists
    edata.export(surfacepath)
    metafile = absolute_path.parent / f".{absolute_path.name}.yml"
    assert absolute_path.exists()
    assert metafile.exists()


def test_export_to_results_folder(
    fmurun_prehook, rmsglobalconfig, regsurf, monkeypatch
):
    """
    Test re-exporting a preprocessed surface in a fmu run, and see that it works
    storing to the case/share/results folder
    """
    # mock being outside of FMU and export preprocessed surface
    remove_ert_env(monkeypatch)
    surfacepath, _ = export_preprocessed_surface(rmsglobalconfig, regsurf)

    # run the re-export of the preprocessed data inside an mocked FMU run
    set_ert_env_prehook(monkeypatch)
    edata = dataio.ExportPreprocessedData(
        config=rmsglobalconfig, is_observation=False, casepath=fmurun_prehook
    )

    # check that the export has been to the case/share/results folder
    relative_path = PREPROCESSED_SURFACEPATH.replace("preprocessed", "results")

    filepath = Path(edata.export(surfacepath))
    assert filepath == fmurun_prehook / relative_path

    metafile = filepath.parent / f".{filepath.name}.yml"
    assert metafile.exists()


def test_outdated_metadata(fmurun_prehook, rmsglobalconfig, regsurf, monkeypatch):
    """
    Test that a warning is given when trying to re-export preprocessed data
    and the existing metadata is not according to the latest data standard.
    Also test that if using generate_metadata directly an error is raised.
    """
    # mock being outside of FMU and export preprocessed surface
    remove_ert_env(monkeypatch)
    surfacepath, metafile = export_preprocessed_surface(rmsglobalconfig, regsurf)

    # modify existing metadata file to make it 'outdated'
    metadata = read_metadata(metafile)
    del metadata["data"]  # pretend data was not required before
    utils.export_metadata_file(file=metafile, metadata=metadata, savefmt="yaml")

    # run the re-export of the preprocessed data inside an mocked FMU run
    set_ert_env_prehook(monkeypatch)

    edata = dataio.ExportPreprocessedData(
        config=rmsglobalconfig, is_observation=True, casepath=fmurun_prehook
    )
    # error should be raised when trying to use the generate_metadata function
    with pytest.raises(InvalidMetadataError, match="outdated"):
        edata.generate_metadata(surfacepath)

    # warning should be printed when trying to use the export function
    with pytest.warns(UserWarning, match="outdated"):
        edata.export(surfacepath)


def test_export_without_existing_meta(
    fmurun_prehook, rmsglobalconfig, regsurf, monkeypatch
):
    """
    Test that a warning is raised if metadata is not existing for a file
    and that the file is copied anyway
    """
    # mock being outside of FMU and export preprocessed surface
    remove_ert_env(monkeypatch)
    surfacepath, metafile = export_preprocessed_surface(rmsglobalconfig, regsurf)

    # run the re-export of the preprocessed data inside an mocked FMU run
    set_ert_env_prehook(monkeypatch)

    # delete the metafile
    metafile.unlink()
    edata = dataio.ExportPreprocessedData(
        config=rmsglobalconfig, is_observation=True, casepath=fmurun_prehook
    )
    # test that error is raised when creating metadata
    with pytest.raises(RuntimeError, match="Could not detect existing metadata"):
        edata.generate_metadata(surfacepath)

    # test that warning is issued when doing an export
    with pytest.warns(UserWarning, match="Could not detect existing metadata"):
        filepath = edata.export(surfacepath)

    # check that the file have been copied into the fmu case path
    assert Path(filepath).exists()
    assert filepath.startswith(str(fmurun_prehook))


def test_preprocessed_surface_modified_post_export(
    fmurun_prehook, rmsglobalconfig, regsurf, monkeypatch
):
    """
    Test that a warning is raised if the md5sum for the file does not match
    the 'file.checksum_md5' in the existing metadata
    """
    # mock being outside of FMU and export preprocessed surface
    remove_ert_env(monkeypatch)
    surfacepath, metafile = export_preprocessed_surface(rmsglobalconfig, regsurf)

    # modify existing metadata file to make the md5sum inconsistent
    metadata = read_metadata(metafile)
    metadata["file"]["checksum_md5"] = "dummy_modified"
    utils.export_metadata_file(file=metafile, metadata=metadata, savefmt="yaml")

    # run the re-export of the preprocessed data inside an mocked FMU run
    set_ert_env_prehook(monkeypatch)

    # should issue warning
    with pytest.warns(UserWarning, match="seem to have been modified"):
        dataio.ExportPreprocessedData(
            config=rmsglobalconfig, is_observation=True, casepath=fmurun_prehook
        ).export(surfacepath)


def test_preprocessed_surface_fmucontext_not_case(rmsglobalconfig, monkeypatch):
    """
    Test that an error is raised if ExportPreprocessedData is used
    in other fmu_context than 'case'
    """

    # error should be raised when outside of FMU
    with pytest.raises(RuntimeError, match="Only possible to run re-export"):
        dataio.ExportPreprocessedData(config=rmsglobalconfig, casepath="dummy")

    # error should be raised when running on forward_model in FMU
    set_ert_env_forward(monkeypatch)
    with pytest.raises(RuntimeError, match="Only possible to run re-export"):
        dataio.ExportPreprocessedData(config=rmsglobalconfig, casepath="dummy")


def test_preprocessed_surface_invalid_casepath(fmurun_prehook, rmsglobalconfig):
    """Test that an error is raised if casepath is wrong or no case meta exist"""

    # error should be raised when running on a casepath without case metadata
    with pytest.raises(ValueError, match="Could not detect valid case metadata"):
        dataio.ExportPreprocessedData(config=rmsglobalconfig, casepath="dummy")

    # shall work when casepath that contains case matadata is provided
    dataio.ExportPreprocessedData(config=rmsglobalconfig, casepath=fmurun_prehook)

    # delete the case matadata and see that it fails
    metacase_file = fmurun_prehook / ERT_RELATIVE_CASE_METADATA_FILE
    metacase_file.unlink()
    with pytest.raises(ValueError, match="Could not detect valid case metadata"):
        dataio.ExportPreprocessedData(config=rmsglobalconfig, casepath=fmurun_prehook)


def test_export_non_preprocessed_data(
    fmurun_prehook, rmsglobalconfig, regsurf, monkeypatch
):
    """Test that if not exported with fmu_context='preprocessed' error is raised"""
    # mock being outside of FMU
    remove_ert_env(monkeypatch)
    surfacepath = dataio.ExportData(
        config=rmsglobalconfig,
        fmu_context=None,
        name="TopVolantis",
        content="depth",
    ).export(regsurf)

    assert "share/results" in surfacepath

    # mock being inside of FMU
    set_ert_env_prehook(monkeypatch)

    # check that the error is given
    with pytest.raises(RuntimeError, match="is not supported"):
        dataio.ExportPreprocessedData(
            config=rmsglobalconfig, is_observation=True, casepath=fmurun_prehook
        ).generate_metadata(surfacepath)


def test_export_preprocessed_file_exportdata_futurewarning(
    fmurun_prehook, rmsglobalconfig, regsurf, monkeypatch
):
    """
    Test that using the ExportData class to export preprocessed files
    still works (uses ExportPreprocessedData behind the scene) and
    a future warning is issued.
    """
    # mock being outside of FMU
    remove_ert_env(monkeypatch)
    surfacepath, _ = export_preprocessed_surface(rmsglobalconfig, regsurf)

    # mock being inside of FMU
    set_ert_env_prehook(monkeypatch)

    # Use the ExportData class instead of the ExportPreprocessedData
    edata = dataio.ExportData(
        config=rmsglobalconfig, is_observation=True, casepath=fmurun_prehook
    )

    with pytest.warns(FutureWarning, match="no longer supported"):
        meta = edata.generate_metadata(surfacepath)

    assert "fmu" in meta
    assert "merged" in meta["tracklog"][-1]["event"]

    with pytest.warns(FutureWarning, match="no longer supported"):
        filepath = Path(edata.export(surfacepath))

    assert filepath.exists()
    metafile = filepath.parent / f".{filepath.name}.yml"
    assert metafile.exists()


def test_export_preprocessed_file_exportdata_casepath_on_export(
    fmurun_prehook, rmsglobalconfig, regsurf, monkeypatch
):
    """
    Test that using the ExportData class to export preprocessed files
    works also if arguments have been given on the export/generate_metadata methods
    """
    # mock being outside of FMU
    remove_ert_env(monkeypatch)
    surfacepath, _ = export_preprocessed_surface(rmsglobalconfig, regsurf)

    # mock being inside of FMU
    set_ert_env_prehook(monkeypatch)

    # Use the ExportData class instead of the ExportPreprocessedData
    edata = dataio.ExportData(config=rmsglobalconfig)

    # test that error is thrown when missing casepath
    with pytest.raises(TypeError, match="No 'casepath' argument provided"):
        edata.export(surfacepath, is_observation=True)

    # test that export() works if casepath is provided
    with pytest.warns(FutureWarning, match="no longer supported"):
        filepath = Path(
            edata.export(surfacepath, is_observation=True, casepath=fmurun_prehook)
        )
    assert filepath.exists()
    metafile = filepath.parent / f".{filepath.name}.yml"
    assert metafile.exists()

    # Use the ExportData class instead of the ExportPreprocessedData
    edata = dataio.ExportData(config=rmsglobalconfig)

    # test that error is thrown when missing casepath
    with pytest.raises(TypeError, match="No 'casepath' argument provided"):
        edata.generate_metadata(surfacepath, is_observation=True)

    # test that generate_metadata() works if casepath is provided
    with pytest.warns(FutureWarning, match="no longer supported"):
        meta = edata.generate_metadata(
            surfacepath, is_observation=True, casepath=fmurun_prehook
        )

    assert "fmu" in meta
    assert "merged" in meta["tracklog"][-1]["event"]
