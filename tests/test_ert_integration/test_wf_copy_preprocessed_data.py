from __future__ import annotations

import getpass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import ert.__main__
import pytest
import yaml
from pytest import CaptureFixture, MonkeyPatch

from fmu import dataio
from fmu.dataio._workflows.copy_preprocessed import (
    _normalize_workflow_arguments,
    get_parser,
)

from .ert_config_utils import (
    add_copy_preprocessed_workflow,
    add_create_case_workflow,
    remove_sumo_casepath_definition,
)

if TYPE_CHECKING:
    import xtgeo
    from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
    from pytest_mock import MockerFixture


def _export_preprocessed_data(
    config: dict | GlobalConfiguration, regsurf: xtgeo.RegularSurface
) -> None:
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


@pytest.mark.parametrize(
    ("workflow_args", "expected"),
    [
        (["preprocessed"], (None, None, "preprocessed")),
        (
            ["/case", "/config", "preprocessed"],
            ("/case", "/config", "preprocessed"),
        ),
    ],
)
def test_normalize_workflow_arguments(
    workflow_args: list[str], expected: tuple[str | None, str | None, str]
) -> None:
    """Current and legacy positional layouts are normalized unambiguously."""
    args = get_parser().parse_args(workflow_args)

    _normalize_workflow_arguments(args)

    assert (args.ert_caseroot, args.ert_config_path, args.inpath) == expected


def test_normalize_workflow_arguments_rejects_two_paths() -> None:
    """The ambiguous two-value positional layout is rejected."""
    args = get_parser().parse_args(["/case", "preprocessed"])

    with pytest.raises(ValueError, match="expects either <inpath>"):
        _normalize_workflow_arguments(args)


def test_copy_preprocessed_runs_successfully(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    drogon_global_config: dict[str, Any],
    regsurf: xtgeo.RegularSurface,
) -> None:
    """Test that exporting preprocessed data works and that the metadata is updated"""
    monkeypatch.chdir(fmu_snakeoil_project)
    _export_preprocessed_data(drogon_global_config, regsurf)
    preprocessed_maps = fmu_snakeoil_project / "share/preprocessed/maps"
    (preprocessed_maps / "linked.gri").symlink_to(preprocessed_maps / "topvolon.gri")

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)
    add_copy_preprocessed_workflow(ert_config_path)

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
    assert not (observations_folder / "maps/linked.gri").exists()

    # check one of the metafiles to see that the fmu block has been added
    metafile = observations_folder / "maps/.topvolon.gri.yml"
    with open(metafile, encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    assert meta["fmu"]["case"]["name"] == "snakeoil"
    assert meta["fmu"]["case"]["user"]["id"] == getpass.getuser()
    assert meta["fmu"]["context"]["stage"] == "case"
    assert len(meta["tracklog"]) == 2


def test_deprecated_path_arguments_warn_and_are_ignored(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    drogon_global_config: dict[str, Any],
    regsurf: xtgeo.RegularSurface,
) -> None:
    """Legacy paths warn while ERT substitutions remain authoritative."""
    monkeypatch.chdir(fmu_snakeoil_project)
    _export_preprocessed_data(drogon_global_config, regsurf)

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"
    legacy_casepath = fmu_snakeoil_project / "scratch/user/legacy"
    legacy_config_path = fmu_snakeoil_project / "legacy/config"

    add_create_case_workflow(ert_config_path)
    add_copy_preprocessed_workflow(
        ert_config_path,
        legacy_arguments=(str(legacy_casepath), str(legacy_config_path)),
    )

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )
    with (
        pytest.warns(FutureWarning, match="'ert_caseroot' is deprecated"),
        pytest.warns(FutureWarning, match="'ert_config_path' is deprecated"),
    ):
        ert.__main__.main()

    expected_file = (
        fmu_snakeoil_project
        / "scratch/user/snakeoil/share/observations/maps/topvolon.gri"
    )
    legacy_file = legacy_casepath / "share/observations/maps/topvolon.gri"
    assert expected_file.exists()
    assert not legacy_file.exists()


def test_copy_preprocessed_requires_sumo_casepath(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    capsys: CaptureFixture[str],
) -> None:
    """The new workflow form requires SUMO_CASEPATH in the ERT config."""
    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"
    remove_sumo_casepath_definition(ert_config_path)
    add_copy_preprocessed_workflow(ert_config_path)

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )
    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "The case path could not be resolved" in stderr


def test_copy_preprocessed_rejects_relative_sumo_casepath(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    capsys: CaptureFixture[str],
) -> None:
    """SUMO_CASEPATH must resolve to an absolute path."""
    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"
    ert_config_path.write_text(
        ert_config_path.read_text().replace(
            "DEFINE <SUMO_CASEPATH>  <SCRATCH>/<USER>/<CASE_DIR>",
            "DEFINE <SUMO_CASEPATH>  relative/path",
        )
    )
    add_copy_preprocessed_workflow(ert_config_path)

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )
    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "'casepath' must be an absolute path. Got: relative/path" in stderr


def test_copy_preprocessed_no_casemeta(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    drogon_global_config: dict[str, Any],
    regsurf: xtgeo.RegularSurface,
    capsys: CaptureFixture[str],
) -> None:
    """Test that an error is written to stderr if no case metadata can be found."""

    monkeypatch.chdir(fmu_snakeoil_project)
    _export_preprocessed_data(drogon_global_config, regsurf)

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_copy_preprocessed_workflow(ert_config_path)

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )
    with pytest.warns(UserWarning, match="metadata"):
        ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: Could not detect valid case metadata" in stderr


def test_copy_preprocessed_no_preprocessed_files(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    capsys: CaptureFixture[str],
) -> None:
    """
    Test that an error is written to stderr if no files can be found.
    Here represented by not running the initial export of preprocessed data
    """

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)
    add_copy_preprocessed_workflow(ert_config_path)

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )

    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "No files found in searchpath" in stderr


def test_inpath_absolute_path_raises(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    capsys: CaptureFixture[str],
) -> None:
    """Test that an error is written to stderr if the inpath argument is absolute"""

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_copy_preprocessed_workflow(ert_config_path, inpath="/absolute/path")

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )

    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: 'inpath' is an absolute path" in stderr


def test_copy_preprocessed_no_preprocessed_meta(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    regsurf: xtgeo.RegularSurface,
) -> None:
    """Test that a pure copy happens if the files don't have metadata"""

    monkeypatch.chdir(fmu_snakeoil_project)

    # an invalid config will trigger no metadata to be created
    with (
        patch(
            "fmu.dataio._export._export_config_resolver.load_global_config",
            side_effect=FileNotFoundError,  # Fall back to user-provided config dict
        ),
        pytest.warns(UserWarning),
    ):
        _export_preprocessed_data({"wrong": "config"}, regsurf)

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)
    add_copy_preprocessed_workflow(ert_config_path)

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
    fmu_snakeoil_project: Path, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
    """Test that deprecation warning is issued if global variables path is input"""

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)
    add_copy_preprocessed_workflow(
        ert_config_path, extra_args="'--global_variables_path' dummypath"
    )

    mocker.patch(
        "sys.argv",
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )

    with pytest.warns(FutureWarning, match="no longer needed"):
        ert.__main__.main()
