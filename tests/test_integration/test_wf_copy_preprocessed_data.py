import ert.__main__
import pytest
import yaml

import fmu.dataio as dataio

from .ert_config_utils import (
    add_copy_preprocessed_workflow,
    add_create_case_workflow,
)


def _export_preprocessed_data(config, regsurf):
    """Export preprocessed surfaces"""
    dataio.ExportData(
        config=config,
        preprocessed=True,
        name="TopVolantis",
        content="depth",
        subfolder="mysubfolder",
    ).export(regsurf)

    dataio.ExportData(
        config=config,
        preprocessed=True,
        name="TopVolon",
        content="depth",
    ).export(regsurf)


def test_copy_preprocessed_runs_successfully(
    fmu_snakeoil_project, monkeypatch, mocker, globalconfig2, regsurf
):
    """Test that exporting preprocessed data works and that the metadata is updated"""
    monkeypatch.chdir(fmu_snakeoil_project)
    _export_preprocessed_data(globalconfig2, regsurf)

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")
    add_copy_preprocessed_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )
    ert.__main__.main()

    fmu_case = fmu_snakeoil_project / "scratch/user/snakeoil"

    fmu_case_yml = fmu_case / "share/metadata/fmu_case.yml"
    assert fmu_case_yml.exists()

    observations_folder = fmu_case / "share/observations"

    assert (observations_folder / "maps/topvolon.gri").exists()
    assert (observations_folder / "maps/.topvolon.gri.yml").exists()
    assert (observations_folder / "maps/mysubfolder/topvolantis.gri").exists()
    assert (observations_folder / "maps/mysubfolder/.topvolantis.gri.yml").exists()

    # check one of the metafiles to see that the fmu block has been added
    metafile = observations_folder / "maps/.topvolon.gri.yml"
    with open(metafile, encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    assert meta["fmu"]["case"]["name"] == "snakeoil"
    assert meta["fmu"]["case"]["user"]["id"] == "user"
    assert meta["fmu"]["context"]["stage"] == "case"
    assert len(meta["tracklog"]) == 2


def test_copy_preprocessed_no_casemeta(
    fmu_snakeoil_project, monkeypatch, mocker, globalconfig2, regsurf, capsys
):
    """Test that an error is written to stderr if no case metadata can be found."""

    monkeypatch.chdir(fmu_snakeoil_project)
    _export_preprocessed_data(globalconfig2, regsurf)

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_copy_preprocessed_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )
    with pytest.warns(UserWarning, match="metadata"):
        ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: Could not detect valid case metadata" in stderr


def test_copy_preprocessed_no_preprocessed_files(
    fmu_snakeoil_project, monkeypatch, mocker, capsys
):
    """
    Test that an error is written to stderr if no files can be found.
    Here represented by not running the initial export of preprocessed data
    """

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")
    add_copy_preprocessed_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )

    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "No files found in searchpath" in stderr


def test_inpath_absolute_path_raises(fmu_snakeoil_project, monkeypatch, mocker, capsys):
    """Test that an error is written to stderr if the inpath argument is absolute"""

    # create a workflow file with an absoulte inpath
    workflow_file = (
        fmu_snakeoil_project / "ert/bin/workflows/xhook_copy_preprocessed_data"
    )
    with open(workflow_file, encoding="utf-8", mode="w") as f:
        f.write(
            "WF_COPY_PREPROCESSED_DATAIO <SCRATCH>/<USER>/<CASE_DIR> <CONFIG_PATH> "
            "/../../share/preprocessed"  # absolute path
        )

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_copy_preprocessed_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )

    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: 'inpath' is an absolute path" in stderr


def test_copy_preprocessed_no_preprocessed_meta(
    fmu_snakeoil_project, monkeypatch, mocker, regsurf
):
    """Test that a pure copy happens if the files don't have metadata"""

    monkeypatch.chdir(fmu_snakeoil_project)
    # an invalid config will trigger no metadata to be created
    with pytest.warns(UserWarning):
        _export_preprocessed_data({"wrong": "config"}, regsurf)

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")
    add_copy_preprocessed_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )

    with pytest.warns(UserWarning, match=r"will be copied.+but without metadata"):
        ert.__main__.main()

    observations_folder = (
        fmu_snakeoil_project / "scratch/user/snakeoil/share/observations"
    )

    assert (observations_folder / "maps/topvolon.gri").exists()
    assert not (observations_folder / "maps/.topvolon.gri.yml").exists()
    assert (observations_folder / "maps/mysubfolder/topvolantis.gri").exists()
    assert not (observations_folder / "maps/mysubfolder/.topvolantis.gri.yml").exists()


def test_deprecation_warning_global_variables(
    fmu_snakeoil_project, monkeypatch, mocker
):
    """Test that deprecation warning is issued if global variables path is input"""

    # add the deprecated argument to the workflow file
    workflow_file = (
        fmu_snakeoil_project / "ert/bin/workflows/xhook_copy_preprocessed_data"
    )
    with open(workflow_file, encoding="utf-8", mode="a") as f:
        f.write(" '--global_variables_path' dummypath")

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_copy_preprocessed_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )

    with pytest.warns(FutureWarning, match="no longer needed"):
        ert.__main__.main()
