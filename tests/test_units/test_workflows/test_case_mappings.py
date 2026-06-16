from pathlib import Path

import pyarrow as pa
from fmu.settings import get_fmu_directory
from fmu.settings._drogon import create_drogon_fmu_dir

from fmu.dataio._workflows.case._mappings import (
    get_stratigraphy_mappings_table,
    has_stratigraphy_mappings,
)


def test_has_stratigraphy_mappings_mapping_file_exists(tmp_path: Path) -> None:
    """Test has_stratigraphy_mappings return True when mappings file exists."""

    fmu_dir = create_drogon_fmu_dir(tmp_path)

    assert has_stratigraphy_mappings(fmu_dir) is True


def test_has_stratigraphy_mappings_no_mapping_file(tmp_path: Path) -> None:
    """Test has_stratigraphy_mappings return False when no mappings file exists."""

    fmu_dir = create_drogon_fmu_dir(tmp_path)
    fmu_dir.mappings.path.unlink()  # Delete mappings file

    fmu_dir = get_fmu_directory(tmp_path)  # Fresh instance

    assert has_stratigraphy_mappings(fmu_dir) is False


def test_has_stratigraphy_mappings_no_mappings_in_file(tmp_path: Path) -> None:
    """
    Test has_stratigraphy_mappings returns False when mappings file exists
    without stratigraphy mappings.
    """
    fmu_dir = create_drogon_fmu_dir(tmp_path)

    # Write empty JSON to mappings file to simulate no stratigraphy mappings
    fmu_dir.mappings.path.write_text("{}")

    fmu_dir = get_fmu_directory(tmp_path)  # Fresh instance

    assert fmu_dir.mappings.exists is True
    assert len(fmu_dir.mappings.stratigraphy_mappings) == 0

    assert has_stratigraphy_mappings(fmu_dir) is False


def test_get_stratigraphy_mappings_table_as_expected(tmp_path: Path) -> None:
    """Test an expected table is returned when mappings exists in .fmu."""
    fmu_dir = create_drogon_fmu_dir(tmp_path)

    mappings_table = get_stratigraphy_mappings_table(fmu_dir)

    assert isinstance(mappings_table, pa.Table)
    assert len(mappings_table) == 11
    assert set(mappings_table.column_names) == {
        "source_system",
        "source_id",
        "source_uuid",
        "target_system",
        "target_id",
        "target_uuid",
        "mapping_type",
        "relation_type",
    }

    mappings = mappings_table.to_pylist()

    assert mappings[0]["source_system"] == "rms"
    assert mappings[0]["target_system"] == "smda"
    assert mappings[0]["source_id"] == "TopVolantis"
    assert mappings[0]["target_id"] == "VOLANTIS GP. Top"
    assert mappings[0]["mapping_type"] == "stratigraphy"
    assert mappings[0]["relation_type"] == "primary"
    assert mappings[0]["source_uuid"] is None
    assert mappings[0]["target_uuid"] == "1629c229-0a2b-4f0a-94f7-dc01b171cb1c"


def test_get_stratigraphy_mappings_table_returns_none_when_no_mappings(
    tmp_path: Path,
) -> None:
    """Test that None is returned when no stratigraphy mappings exist."""

    fmu_dir = create_drogon_fmu_dir(tmp_path)
    fmu_dir.mappings.path.unlink()  # Delete mappings file

    fmu_dir = get_fmu_directory(tmp_path)  # Fresh instance
    assert get_stratigraphy_mappings_table(fmu_dir) is None
