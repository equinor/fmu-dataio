import getpass
import importlib
import os
import sys

import ert.__main__
import pytest
import yaml


def _add_create_case_workflow(filepath):
    with open(filepath, "a", encoding="utf-8") as f:
        f.writelines(
            [
                "LOAD_WORKFLOW ../bin/workflows/xhook_create_case_metadata\n"
                "HOOK_WORKFLOW xhook_create_case_metadata PRE_SIMULATION\n"
            ]
        )


def test_create_case_metadata_runs_successfully(
    fmu_snakeoil_project, monkeypatch, mocker
):
    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    _add_create_case_workflow("snakeoil.ert")

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
    assert fmu_case["fmu"]["case"]["user"]["id"] == "user"
    assert fmu_case["source"] == "fmu"
    assert len(fmu_case["tracklog"]) == 1
    assert fmu_case["tracklog"][0]["user"]["id"] == getpass.getuser()


def test_create_case_metadata_warns_without_overwriting(
    fmu_snakeoil_project, monkeypatch, mocker
):
    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    _add_create_case_workflow("snakeoil.ert")

    share_metadata = fmu_snakeoil_project / "scratch/user/snakeoil/share/metadata"
    fmu_case_yml = share_metadata / "fmu_case.yml"

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    assert fmu_case_yml.exists()
    with open(fmu_case_yml, encoding="utf-8") as f:
        first_run = yaml.safe_load(f)

    with pytest.warns(UserWarning, match="The case metadata file already exists"):
        ert.__main__.main()

    ls_share_metadata = os.listdir(share_metadata)
    assert ls_share_metadata == ["fmu_case.yml"]

    with open(fmu_case_yml, encoding="utf-8") as f:
        second_run = yaml.safe_load(f)

    assert first_run == second_run


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo"),
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
        f.write(' "--sumo" "--sumo_env" <SUMO_ENV>')

    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    _add_create_case_workflow("snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    # Verifies case.register() was run
    with open("sumo_case_id", encoding="utf-8") as f:
        assert f.read() == "1"
