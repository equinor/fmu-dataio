from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fmu.dataio._workflows._utils import resolve_casepath, validate_casepath


def test_validate_casepath_returns_absolute_path() -> None:
    casepath = Path("/tmp/scratch/user/case")

    assert validate_casepath(casepath) == casepath


def test_validate_casepath_raises_for_relative_path() -> None:
    with pytest.raises(ValueError, match="'casepath' must be an absolute path"):
        validate_casepath(Path("relative/case"))


def test_validate_casepath_raises_for_unresolved_ert_variable() -> None:
    with pytest.raises(ValueError, match="Ert variable for casepath is not defined"):
        validate_casepath(Path("<SUMO_CASEPATH>"))


def test_resolve_casepath_uses_sumo_casepath_when_defined() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = {"<SUMO_CASEPATH>": "/tmp/scratch/user/case"}

    assert resolve_casepath(run_paths, legacy_casepath=None) == Path(
        "/tmp/scratch/user/case"
    )


def test_resolve_casepath_warns_when_legacy_casepath_is_provided() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = {"<SUMO_CASEPATH>": "/tmp/scratch/user/case"}

    with pytest.warns(FutureWarning, match="Providing the case path as argument"):
        resolved = resolve_casepath(run_paths, legacy_casepath="/tmp/legacy/case")

    assert resolved == Path("/tmp/scratch/user/case")


def test_resolve_casepath_uses_legacy_casepath_when_allowed() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = {}  # missing <SUMO_CASEPATH>

    assert resolve_casepath(run_paths, legacy_casepath="/tmp/legacy/case") == Path(
        "/tmp/legacy/case"
    )


def test_resolve_casepath_raises_when_sumo_required_but_missing() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = {}  # missing <SUMO_CASEPATH>

    with pytest.raises(ValueError, match="Missing required <SUMO_CASEPATH> definition"):
        resolve_casepath(
            run_paths,
            legacy_casepath="/tmp/legacy/case",
            require_sumo_casepath=True,
        )


def test_resolve_casepath_raises_when_no_casepath_is_available() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = {}  # missing <SUMO_CASEPATH>

    with pytest.raises(ValueError, match="The case path could not be resolved"):
        resolve_casepath(run_paths, legacy_casepath=None)
