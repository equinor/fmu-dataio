from __future__ import annotations

from pathlib import Path

import pytest

from fmu.dataio._definitions import FmuSchemas, SchemaBase


def test_schemabase_validates_class_vars() -> None:
    """Tests that light validation on the schema base class functions."""
    with pytest.raises(TypeError, match="Subclass A must define 'PATH'"):

        class A(SchemaBase):
            VERSION: str = "0.8.0"
            FILENAME: str = "fmu_results.json"

    with pytest.raises(TypeError, match="Subclass B must define 'FILENAME'"):

        class B(SchemaBase):
            VERSION: str = "0.8.0"
            PATH: Path = FmuSchemas.PATH / "test"

    with pytest.raises(TypeError, match="Subclass C must define 'VERSION'"):

        class C(SchemaBase):
            FILENAME: str = "fmu_results.json"
            PATH: Path = FmuSchemas.PATH / "test"


def test_schemabase_requires_path_starting_with_fmuschemas_path() -> None:
    """Tests that SchemaBase catches if a subclass's PATH does not fall into the main
    schemas directory."""
    with pytest.raises(
        ValueError, match=f"PATH must start with `FmuSchemas.PATH`: {FmuSchemas.PATH}"
    ):

        class A(SchemaBase):
            VERSION: str = "0.8.0"
            FILENAME: str = "fmu_results.json"
            PATH: Path = Path("test")
