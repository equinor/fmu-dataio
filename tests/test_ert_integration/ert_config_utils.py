from __future__ import annotations

from pathlib import Path


def add_create_case_workflow(ert_config_path: Path | str) -> None:
    with open(ert_config_path, "a", encoding="utf-8") as f:
        f.writelines(
            [
                "LOAD_WORKFLOW ../bin/workflows/xhook_create_case_metadata\n"
                "HOOK_WORKFLOW xhook_create_case_metadata PRE_SIMULATION\n"
            ]
        )


def add_copy_preprocessed_workflow(ert_config_path: Path | str) -> None:
    with open(ert_config_path, "a", encoding="utf-8") as f:
        f.writelines(
            [
                "LOAD_WORKFLOW ../bin/workflows/xhook_copy_preprocessed_data\n"
                "HOOK_WORKFLOW xhook_copy_preprocessed_data PRE_SIMULATION\n"
            ]
        )


def add_export_a_surface_forward_model(
    project_path: Path, ert_config_path: Path | str
) -> None:
    with open(ert_config_path, "a", encoding="utf-8") as f:
        f.writelines(
            [
                "INSTALL_JOB EXPORT_A_SURFACE ../bin/jobs/EXPORT_A_SURFACE\n"
                f"FORWARD_MODEL EXPORT_A_SURFACE(<PROJECT_PATH>={project_path})\n"
            ]
        )
