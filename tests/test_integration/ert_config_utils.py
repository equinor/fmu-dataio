from __future__ import annotations

from pathlib import Path


def add_create_case_workflow(filepath: Path | str) -> None:
    with open(filepath, "a", encoding="utf-8") as f:
        f.writelines(
            [
                "LOAD_WORKFLOW ../bin/workflows/xhook_create_case_metadata\n"
                "HOOK_WORKFLOW xhook_create_case_metadata PRE_SIMULATION\n"
            ]
        )


def add_copy_preprocessed_workflow(filepath: Path | str) -> None:
    with open(filepath, "a", encoding="utf-8") as f:
        f.writelines(
            [
                "LOAD_WORKFLOW ../bin/workflows/xhook_copy_preprocessed_data\n"
                "HOOK_WORKFLOW xhook_copy_preprocessed_data PRE_SIMULATION\n"
            ]
        )


def add_export_a_surface_forward_model(
    snakeoil_path: Path, filepath: Path | str
) -> None:
    with open(filepath, "a", encoding="utf-8") as f:
        f.writelines(
            [
                "INSTALL_JOB EXPORT_A_SURFACE ../bin/jobs/EXPORT_A_SURFACE\n"
                f"FORWARD_MODEL EXPORT_A_SURFACE(<SNAKEOIL_PATH>={snakeoil_path})\n"
            ]
        )
