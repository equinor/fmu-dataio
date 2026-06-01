"""Extract and process stratigraphy mappings."""

from __future__ import annotations

import logging
from typing import Final

import pyarrow as pa

from fmu.settings import ProjectFMUDirectory

logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


def has_stratigraphy_mappings(fmu_dir: ProjectFMUDirectory) -> bool:
    """Check if any stratigraphy mappings exist in .fmu."""
    return fmu_dir.mappings.exists and len(fmu_dir.mappings.stratigraphy_mappings) > 0


def get_stratigraphy_mappings_table(fmu_dir: ProjectFMUDirectory) -> pa.Table | None:
    """Extract stratigraphy mappings from .fmu and process it into an arrow table."""
    if not has_stratigraphy_mappings(fmu_dir):
        return None

    return pa.Table.from_pylist(
        fmu_dir.mappings.stratigraphy_mappings.model_dump(mode="json"),
    )
