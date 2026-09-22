import warnings
from pathlib import Path

from ert.runpaths import Runpaths as ErtRunpaths


def validate_casepath(casepath: Path) -> Path:
    """Validate that the case path is absolute and defined in the ERT config."""
    if not casepath.is_absolute():
        casepath_str = str(casepath)
        if casepath_str.startswith("<") and casepath_str.endswith(">"):
            raise ValueError(f"Ert variable for casepath is not defined: {casepath}")
        raise ValueError(f"'casepath' must be an absolute path. Got: {casepath}")
    return casepath


def resolve_casepath(
    run_paths: ErtRunpaths,
    legacy_casepath: str | None,
    require_sumo_casepath: bool = False,
) -> Path:
    """Resolve and validate case path from <SUMO_CASEPATH> or deprecated argument.

    Uses <SUMO_CASEPATH> when defined and warns if deprecated <casepath> argument
    is also provided. If Sumo is enabled but <SUMO_CASEPATH> is missing, an error
    is raised, otherwise it falls back to <casepath> argument if provided.
    """

    sumo_casepath = run_paths.substitutions.get("<SUMO_CASEPATH>")

    if sumo_casepath:
        if legacy_casepath:
            warnings.warn(
                "Providing the case path as argument is deprecated. "
                "It is no longer used and can safely be removed from the workflow. "
                "The case path is now read from the <SUMO_CASEPATH> variable.",
                FutureWarning,
            )
        return validate_casepath(Path(sumo_casepath))

    if legacy_casepath:
        if require_sumo_casepath:
            raise ValueError(
                "Missing required <SUMO_CASEPATH> definition. "
                "Define it in your ERT config, for example:\n"
                "DEFINE <SUMO_CASEPATH> <SCRATCH>/<USER>/<CASE_DIR>"
            )
        return validate_casepath(Path(legacy_casepath))

    raise ValueError(
        "The case path could not be resolved. Please define the "
        "<SUMO_CASEPATH> variable in the ERT config, for example:\n"
        "DEFINE <SUMO_CASEPATH> <SCRATCH>/<USER>/<CASE_DIR>"
    )
