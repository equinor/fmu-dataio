import subprocess

import yaml


def test_create_case_metadata_runs_successfully(fmu_snakeoil_project, monkeypatch):
    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    with open("snakeoil.ert", "a", encoding="utf-8") as f:
        f.writelines(
            [
                "LOAD_WORKFLOW ../bin/workflows/xhook_create_case_metadata\n"
                "HOOK_WORKFLOW xhook_create_case_metadata PRE_SIMULATION\n"
            ]
        )
    run_result = subprocess.run(
        ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
    )
    assert run_result.returncode == 0

    fmu_case_yml = (
        fmu_snakeoil_project / "scratch/user/snakeoil/share/metadata/fmu_case.yml"
    )
    assert fmu_case_yml.exists()

    with open(fmu_case_yml, encoding="utf-8") as f:
        fmu_case = yaml.safe_load(f)
    assert fmu_case["fmu"]["case"]["name"] == "snakeoil"
    assert fmu_case["fmu"]["case"]["user"]["id"] == "user"
    assert fmu_case["source"] == "fmu"
