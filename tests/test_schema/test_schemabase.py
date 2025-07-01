from __future__ import annotations

from pathlib import Path

import pytest

from fmu.datamodels._schema_base import FmuSchemas, SchemaBase


def test_schemabase_validates_class_vars() -> None:
    """Tests that light validation on the schema base class functions."""
    with pytest.raises(TypeError, match="Subclass A must define 'PATH'"):

        class A(SchemaBase):
            VERSION: str = "0.8.0"
            VERSION_CHANGELOG: str = "### 0.8.0"
            FILENAME: str = "fmu_results.json"

    with pytest.raises(TypeError, match="Subclass B must define 'FILENAME'"):

        class B(SchemaBase):
            VERSION: str = "0.8.0"
            VERSION_CHANGELOG: str = "### 0.8.0"
            PATH: Path = FmuSchemas.PATH / "test"

    with pytest.raises(TypeError, match="Subclass C must define 'VERSION'"):

        class C(SchemaBase):
            VERSION_CHANGELOG: str = "### 0.8.0"
            FILENAME: str = "fmu_results.json"
            PATH: Path = FmuSchemas.PATH / "test"

    with pytest.raises(TypeError, match="Subclass D must define 'VERSION_CHANGELOG'"):

        class D(SchemaBase):
            VERSION: str = "0.8.0"
            FILENAME: str = "fmu_results.json"
            PATH: Path = FmuSchemas.PATH / "test"


def test_schemabase_validates_version_string_form() -> None:
    """Tests that the VERSION given to the schema raises if not of a valid form."""
    with pytest.raises(TypeError, match="Invalid VERSION format for 'MajorMinor'"):

        class MajorMinor(SchemaBase):
            VERSION = "12.3"
            VERSION_CHANGELOG: str = "### 12.3"
            FILENAME: str = "fmu_results.json"
            PATH: Path = FmuSchemas.PATH / "test"

    with pytest.raises(TypeError, match="Invalid VERSION format for 'Alphanumeric'"):

        class Alphanumeric(SchemaBase):
            VERSION = "1.3.a"
            VERSION_CHANGELOG: str = "### 1.3.a"
            FILENAME: str = "fmu_results.json"
            PATH: Path = FmuSchemas.PATH / "test"

    with pytest.raises(TypeError, match="Invalid VERSION format for 'LeadingZero'"):

        class LeadingZero(SchemaBase):
            VERSION = "01.3.0"
            VERSION_CHANGELOG: str = "### 01.3.0"
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
            VERSION_CHANGELOG: str = "### 0.8.0"
            FILENAME: str = "fmu_results.json"
            PATH: Path = Path("test")


def test_schemabase_validates_a_version_has_a_changelog_entry() -> None:
    """Tests that a version change has a corresponding changelog entry."""
    with pytest.raises(
        ValueError, match="No changelog entry exists for 'A' version 0.9.0"
    ):

        class A(SchemaBase):
            VERSION: str = "0.9.0"
            VERSION_CHANGELOG: str = ""
            FILENAME: str = "fmu_results.json"
            PATH: Path = FmuSchemas.PATH / "test"

    # Should not raise ValueError
    class B(SchemaBase):
        VERSION: str = "0.9.0"
        VERSION_CHANGELOG: str = "### 0.9.0"
        FILENAME: str = "fmu_results.json"
        PATH: Path = FmuSchemas.PATH / "test"
