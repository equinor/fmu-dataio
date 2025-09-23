import getpass
import importlib
import os
import pathlib
import sys

import ert.__main__
import pytest
import yaml

from .ert_config_utils import add_create_case_workflow


def test_create_case_metadata_runs_successfully(
    fmu_snakeoil_project, monkeypatch, mocker
):
    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    fmu_case_yml = (
        fmu_snakeoil_project / "scratch/user/snakeoil/share/metadata/fmu_case.yml"
    )
    assert fmu_case_yml.exists()

    with open(fmu_case_yml, encoding="utf-8") as f:
        fmu_case = yaml.safe_load(f)

    assert fmu_case["fmu"]["case"]["name"] == "snakeoil"
    assert fmu_case["fmu"]["case"]["user"]["id"] == getpass.getuser()
    assert fmu_case["source"] == "fmu"
    assert len(fmu_case["tracklog"]) == 1
    assert fmu_case["tracklog"][0]["user"]["id"] == getpass.getuser()


def test_create_case_metadata_warns_without_overwriting(
    fmu_snakeoil_project, monkeypatch, mocker
):
    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")

    share_metadata = fmu_snakeoil_project / "scratch/user/snakeoil/share/metadata"
    fmu_case_yml = share_metadata / "fmu_case.yml"

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    assert fmu_case_yml.exists()
    with open(fmu_case_yml, encoding="utf-8") as f:
        first_run = yaml.safe_load(f)

    with pytest.warns(UserWarning, match="Using existing case metadata from casepath:"):
        ert.__main__.main()

    ls_share_metadata = os.listdir(share_metadata)
    assert ls_share_metadata == ["fmu_case.yml"]

    with open(fmu_case_yml, encoding="utf-8") as f:
        second_run = yaml.safe_load(f)

    assert first_run == second_run


def test_create_case_metadata_caseroot_not_defined(
    fmu_snakeoil_project, monkeypatch, mocker, capsys
):
    """Test that a proper error message is given if the case root is
    input as an undefined ERT variable"""
    pathlib.Path(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata"
    ).write_text(
        "WF_CREATE_CASE_METADATA <CASEPATH_NOT_DEFINED> <CONFIG_PATH> <CASE_DIR>",
        encoding="utf-8",
    )
    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: ERT variable used for the case root is not defined" in stderr


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_enable_mocked_sumo(
    fmu_snakeoil_project, monkeypatch, mocker, mock_sumo_uploader
):
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo" "--sumo_env" prod')

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    with pytest.warns(FutureWarning, match="'sumo_env' is ignored"):
        ert.__main__.main()

    # Verifies case.register() was run
    with open("sumo_case_id", encoding="utf-8") as f:
        assert f.read() == "1"


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_dev_input_fails(
    fmu_snakeoil_project, monkeypatch, mocker, mock_sumo_uploader, capsys
):
    """Test that if the sumo_env argument is input as dev it raises an error"""
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo" "--sumo_env" dev')

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: Setting sumo environment through argument" in stderr
    assert "SUMO_ENV" in stderr


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_reads_from_environment(
    fmu_snakeoil_project, monkeypatch, mocker, mock_sumo_uploader
):
    """Test that sumo_env is set through the 'SUMO_ENV' environment variable"""
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo"')

    sumo_env = "dev"
    monkeypatch.setenv("SUMO_ENV", sumo_env)

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    mock_sumo_uploader["SumoConnection"].assert_called_once_with(sumo_env)


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_defaults_to_prod(
    fmu_snakeoil_project, monkeypatch, mocker, mock_sumo_uploader
):
    """Test that sumo_env is defaulted to 'prod' when not set through the environment"""
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo"')

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    # should default to prod when not set
    mock_sumo_uploader["SumoConnection"].assert_called_once_with("prod")


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_input_is_ignored(
    fmu_snakeoil_project, monkeypatch, mocker, mock_sumo_uploader
):
    """Test that the environment variable is used over the sumo_env argument"""
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo" "--sumo_env" prod')

    sumo_env_expected = "dev"
    monkeypatch.setenv("SUMO_ENV", sumo_env_expected)

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    with pytest.warns(FutureWarning, match="'sumo_env' is ignored"):
        ert.__main__.main()

    mock_sumo_uploader["SumoConnection"].assert_called_once_with(sumo_env_expected)
