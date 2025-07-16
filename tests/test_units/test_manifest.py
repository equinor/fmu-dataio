from pathlib import Path

import pytest

from fmu.dataio import ExportData, ExportPreprocessedData
from fmu.dataio.manifest._manifest import (
    MANIFEST_FILENAME,
    get_manifest_path,
    load_export_manifest,
)
from fmu.dataio.manifest._models import ExportManifest

from ..conftest import remove_ert_env, set_ert_env_prehook


def test_export_manifest_from_file(tmp_path):
    """Test that the export manifest can be loaded from a file."""

    # Check that the manifest file does not exist initially
    assert not (tmp_path / MANIFEST_FILENAME).exists()

    # Create a temporary manifest file
    manifest = ExportManifest()
    manifest.add_entry(Path("path_to_object.gri"))
    manifest.add_entry(Path("path_to_another_object.gri"))
    manifest.to_file(tmp_path / MANIFEST_FILENAME)

    assert (tmp_path / MANIFEST_FILENAME).exists()

    # Load the manifest from file
    manifest = ExportManifest.from_file(tmp_path / MANIFEST_FILENAME)
    assert manifest is not None
    assert isinstance(manifest, ExportManifest)

    assert len(manifest) == 2
    assert manifest[0].absolute_path == Path("path_to_object.gri")
    assert manifest[1].absolute_path == Path("path_to_another_object.gri")


def test_export_manifest_from_file_not_exist(tmp_path):
    """Test that an error is raised when trying to load a non-existing manifest file."""

    assert not (tmp_path / MANIFEST_FILENAME).exists()

    # Load the manifest from file
    with pytest.raises(FileNotFoundError):
        ExportManifest.from_file(tmp_path / MANIFEST_FILENAME)


def test_get_manifest_path_realization_context(fmurun_w_casemetadata):
    """Test that the manifest path is correctly derived in a realization context."""
    # check test assumption that the fixture points to the runpath
    assert fmurun_w_casemetadata.name == "iter-0"

    manifest_path = get_manifest_path()
    # check that the manifest path is correct
    assert manifest_path == fmurun_w_casemetadata / MANIFEST_FILENAME


def test_get_manifest_path_case_context(fmurun_prehook):
    """Test that the manifest path is correctly derived in a case context."""
    # check test assumption that the fixture points to the casepath
    assert fmurun_prehook.name == "ertrun1"

    manifest_path = get_manifest_path(casepath=fmurun_prehook)
    # check that the manifest path is correct
    assert manifest_path == fmurun_prehook / MANIFEST_FILENAME


def test_get_manifest_path_case_context_no_casepath(fmurun_prehook):
    """Test that an error is raised when no casepath is provided in case context."""
    with pytest.raises(ValueError):
        get_manifest_path(casepath=None)


def test_manifest_realization_context(fmurun_w_casemetadata, globalconfig1, regsurf):
    """Test that the manifest is created at the runpath in a realization context."""
    runpath = fmurun_w_casemetadata
    casepath = fmurun_w_casemetadata.parent.parent

    ExportData(
        config=globalconfig1,
        content="depth",
        name="test0",
    ).export(regsurf)

    assert (runpath / MANIFEST_FILENAME).exists()
    # should be no manifest at the casepath
    assert not (casepath / MANIFEST_FILENAME).exists()
    manifest = load_export_manifest()
    assert isinstance(manifest, ExportManifest)

    assert len(manifest) == 1
    assert manifest[0].absolute_path == runpath / "share/results/maps/test0.gri"
    assert manifest[0].exported_at is not None
    assert manifest[0].exported_by is not None


def test_manifest_multiple_exports_realization_context(
    fmurun_w_casemetadata, globalconfig1, regsurf
):
    """Test that multiple exports creates and appends to a manifest at the runpath
    in a realization context."""
    runpath = fmurun_w_casemetadata
    casepath = fmurun_w_casemetadata.parent.parent

    for idx in range(3):
        ExportData(
            config=globalconfig1,
            content="depth",
            name=f"test{idx}",
        ).export(regsurf)

    assert (runpath / MANIFEST_FILENAME).exists()
    # should be no manifest at the casepath
    assert not (casepath / MANIFEST_FILENAME).exists()
    manifest = load_export_manifest()

    assert len(manifest) == 3
    assert manifest[0].absolute_path == runpath / "share/results/maps/test0.gri"
    assert manifest[1].absolute_path == runpath / "share/results/maps/test1.gri"
    assert manifest[2].absolute_path == runpath / "share/results/maps/test2.gri"


def test_manifest_case_context(fmurun_prehook, globalconfig1, regsurf):
    """Test that the manifest is created at the casepath in a case context."""

    casepath = fmurun_prehook

    ExportData(
        config=globalconfig1,
        content="depth",
        name="test0",
        casepath=casepath,
    ).export(regsurf)

    assert (casepath / MANIFEST_FILENAME).exists()
    manifest = load_export_manifest(casepath)
    assert isinstance(manifest, ExportManifest)

    assert len(manifest) == 1
    assert manifest[0].absolute_path == casepath / "share/results/maps/test0.gri"
    assert manifest[0].exported_at is not None
    assert manifest[0].exported_by is not None


def test_manifest_multiple_exports_case_context(fmurun_prehook, globalconfig1, regsurf):
    """Test that multiple exports creates and appends to a manifest at the casepath
    in a case context."""
    casepath = fmurun_prehook
    for idx in range(3):
        ExportData(
            config=globalconfig1,
            content="depth",
            name=f"test{idx}",
            casepath=casepath,
        ).export(regsurf)

    assert (casepath / MANIFEST_FILENAME).exists()
    manifest = load_export_manifest(casepath)

    assert len(manifest) == 3
    assert manifest[0].absolute_path == casepath / "share/results/maps/test0.gri"
    assert manifest[1].absolute_path == casepath / "share/results/maps/test1.gri"
    assert manifest[2].absolute_path == casepath / "share/results/maps/test2.gri"


@pytest.mark.usefixtures("inside_rms_interactive")
def test_manifest_rms_interactive(tmp_path, globalconfig1, regsurf, monkeypatch):
    """Test that no manifest is created when running RMS interactively."""

    rms_model_path = tmp_path / "rms/model"
    rms_model_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(rms_model_path)

    edata = ExportData(
        config=globalconfig1,
        content="depth",
        name="test0",
    )
    edata.export(regsurf)

    exportroot = edata._runcontext.exportroot
    assert exportroot == rms_model_path.parent.parent

    # check that the export file and metadata is created
    assert (exportroot / "share/results/maps/test0.gri").exists()
    assert (exportroot / "share/results/maps/.test0.gri.yml").exists()

    # check two places that the manifest is not present
    assert not (exportroot / MANIFEST_FILENAME).exists()
    assert not (rms_model_path / MANIFEST_FILENAME).exists()


def test_load_export_manifest_file_not_exist(tmp_path):
    """Test that an error is raised when trying to load a non-existing manifest file."""

    assert not (tmp_path / MANIFEST_FILENAME).exists()

    with pytest.raises(FileNotFoundError, match="manifest file not found"):
        load_export_manifest(tmp_path / MANIFEST_FILENAME)


def test_export_preprocessed_surface_appends_to_case_manifest(
    fmurun_prehook, globalconfig1, regsurf, monkeypatch
):
    casepath = fmurun_prehook
    monkeypatch.chdir(casepath)

    remove_ert_env(monkeypatch)
    export_data = ExportData(
        config=globalconfig1,
        preprocessed=True,
        name="TopVolantis",
        content="depth",
        timedata=[[20240802, "moni"], [20200909, "base"]],
        casepath=casepath,
    )
    surface_path = Path(export_data.export(regsurf))
    with pytest.raises(FileNotFoundError, match="manifest file not found"):
        load_export_manifest(casepath)

    set_ert_env_prehook(monkeypatch)
    preprocessed_surface_path = ExportPreprocessedData(
        is_observation=False, casepath=casepath
    ).export(surface_path)

    manifest = load_export_manifest(casepath)
    assert len(manifest) == 1
    assert manifest[0].absolute_path == Path(preprocessed_surface_path)
