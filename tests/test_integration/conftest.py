import contextlib
import os
import pathlib
import shutil
from textwrap import dedent
from unittest.mock import patch

import pytest


@pytest.fixture
def base_ert_config() -> str:
    return dedent(
        r"""
        DEFINE <USER>       user
        DEFINE <SCRATCH>    $DATAIO_TMP_PATH/scratch
        DEFINE <CASE_DIR>   snakeoil

        DEFINE <SUMO_ENV>       dev
        DEFINE <SUMO_CASEPATH>  <SCRATCH>/<USER>/<CASE_DIR>

        NUM_REALIZATIONS 5

        QUEUE_SYSTEM LOCAL
        QUEUE_OPTION LOCAL MAX_RUNNING 5

        RANDOM_SEED 123456

        RUNPATH  <SCRATCH>/<USER>/<CASE_DIR>/realization-<IENS>/iter-<ITER>/
    """
    )


@pytest.fixture
def fmu_snakeoil_project(tmp_path, monkeypatch, base_ert_config, global_config2_path):
    """Makes a skeleton FMU project structure into a tmp_path, copying global_config2
    into it with a basic ert config that can be appended onto."""
    monkeypatch.setenv("DATAIO_TMP_PATH", str(tmp_path))

    os.makedirs(tmp_path / "eclipse/model")
    for app in ("ert", "rms"):
        os.makedirs(tmp_path / f"{app}/bin")
        os.makedirs(tmp_path / f"{app}/input")
        os.makedirs(tmp_path / f"{app}/model")
    os.makedirs(tmp_path / "rms/model/snakeoil.rms13.1.2")

    os.makedirs(tmp_path / "fmuconfig/output")
    shutil.copy(global_config2_path, tmp_path / "fmuconfig/output/")

    os.makedirs(tmp_path / "ert/bin/workflows")
    pathlib.Path(tmp_path / "ert/bin/workflows/xhook_create_case_metadata").write_text(
        "WF_CREATE_CASE_METADATA "
        "<SCRATCH>/<USER>/<CASE_DIR> "  # ert case root
        "<CONFIG_PATH> "  # ert config path
        "<CASE_DIR> "  # ert case dir
        "<USER>",  # ert username
        encoding="utf-8",
    )

    pathlib.Path(tmp_path / "ert/model/snakeoil.ert").write_text(
        base_ert_config, encoding="utf-8"
    )

    return tmp_path


@pytest.fixture
def mock_sumo_uploader():
    def register_side_effect(*args, **kwargs):
        with open("sumo_case_id", "w", encoding="utf-8") as f:
            f.write("1")
        return 1

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("fmu.sumo.uploader.SumoConnection", spec=True))
        stack.enter_context(
            patch(
                "fmu.sumo.uploader.CaseOnDisk.register",
                side_effect=register_side_effect,
            )
        )
        yield
