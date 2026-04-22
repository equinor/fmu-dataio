from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pandas as pd


def add_design_matrix(ert_config_path: Path) -> None:
    design_df = pd.DataFrame(
        {
            "REAL": [0, 1, 2],
            "design_a": [1, 2, 3],
            "design_b": [4, 5, 6],
            "design_c": [7, 8, 9],
        },
    )
    design_excel = "design.xlsx"
    design_df.to_excel(
        ert_config_path.parent / design_excel,
        index=False,
        sheet_name="DesignSheet",
    )

    with open(ert_config_path, "a") as f:
        f.writelines([f"DESIGN_MATRIX {design_excel}\n"])


def add_globvar_parameters(ert_config_path: Path) -> None:
    globvar_dist = "globvars.dist"

    with open(ert_config_path.parent / globvar_dist, "w") as f:
        f.writelines(
            [
                "globvar_a LOGUNIF  0.1 10\n",
                "globvar_b UNIFORM  -1   1\n",
                "globvar_c CONST    1050.0\n",
            ]
        )

    with open(ert_config_path, "a") as f:
        f.writelines([f"GEN_KW GLOBVAR {globvar_dist}\n"])


def add_multregt_parameters(ert_config_path: Path) -> None:
    multregt_dist = "multregt.dist"

    with open(ert_config_path.parent / multregt_dist, "w") as f:
        f.writelines(
            [
                "multregt_a LOGUNIF  1E-6  1\n",
                "multregt_b LOGUNIF  1E-6  1E-1\n",
                "multregt_c LOGUNIF  1E-6  1E-2\n",
            ]
        )

    with open(ert_config_path, "a", encoding="utf-8") as f:
        f.writelines([f"GEN_KW MULTREGT {multregt_dist}\n"])


def add_create_case_workflow(ert_config_path: Path) -> None:
    with open(ert_config_path, "a") as f:
        f.writelines(
            [
                "LOAD_WORKFLOW ../bin/workflows/xhook_create_case_metadata\n"
                "HOOK_WORKFLOW xhook_create_case_metadata PRE_SIMULATION\n"
            ]
        )


def add_copy_preprocessed_workflow(ert_config_path: Path) -> None:
    with open(ert_config_path, "a") as f:
        f.writelines(
            [
                "LOAD_WORKFLOW ../bin/workflows/xhook_copy_preprocessed_data\n"
                "HOOK_WORKFLOW xhook_copy_preprocessed_data PRE_SIMULATION\n"
            ]
        )


def add_export_a_surface_forward_model(
    project_path: Path, ert_config_path: Path
) -> None:
    with open(ert_config_path, "a") as f:
        f.writelines(
            [
                "INSTALL_JOB EXPORT_A_SURFACE ../bin/jobs/EXPORT_A_SURFACE\n"
                f"FORWARD_MODEL EXPORT_A_SURFACE(<PROJECT_PATH>={project_path})\n"
            ]
        )


def add_observation_config(ert_config_path: Path) -> None:
    with open(ert_config_path, "a") as f:
        f.write("OBS_CONFIG observations\n")


def add_rft_observations(ert_config_path: Path) -> None:
    obs_config = dedent(
        """
        RFT_OBSERVATION rft_obs
        {
            WELL=R_A6;
            DATE=2018-01-01;
            PROPERTY=PRESSURE;
            VALUE=3800;
            ERROR=30.5;
            TVD=8400;
            EAST=9500;
            NORTH=10500.5;
            ZONE=ZONE1;
        };
        """
    )

    with open(ert_config_path.parent / "observations", "a") as f:
        f.write(obs_config)


def add_summary_observations(ert_config_path: Path) -> None:
    obs_config = dedent(
        """
        SUMMARY_OBSERVATION FOPR_1
        {
        VALUE      = 0.9;
        ERROR      = 0.05;
        DATE       = 2020-01-01;
        KEY        = FOPR;
        };
        SUMMARY_OBSERVATION FGPT_1
        {
        VALUE      = 100.5;
        ERROR      = 10;
        DATE       = 2025-01-01;
        KEY        = FGPT;
        };
        """
    )
    with open(ert_config_path.parent / "observations", "a") as f:
        f.write(obs_config)
