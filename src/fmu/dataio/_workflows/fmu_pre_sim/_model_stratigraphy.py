"""Extract model stratigraphy tables from FMU Settings."""

from __future__ import annotations

import pyarrow as pa

from fmu.settings import ProjectFMUDirectory


def get_model_stratigraphy_horizons_table(
    fmu_dir: ProjectFMUDirectory,
) -> pa.Table | None:
    """Return the ordered RMS model horizons as an Arrow table."""
    config = fmu_dir.config.load()
    if config is None or config.rms is None or not config.rms.horizons:
        return None

    rows = [
        horizon.model_dump(mode="json") | {"stratigraphic_order": order}
        for order, horizon in enumerate(config.rms.horizons)
    ]
    return pa.Table.from_pylist(rows)


def get_model_stratigraphy_zones_table(
    fmu_dir: ProjectFMUDirectory,
) -> pa.Table | None:
    """Return the RMS model zones as an Arrow table."""
    config = fmu_dir.config.load()
    if config is None or config.rms is None or not config.rms.zones:
        return None

    rows = [
        zone.model_dump(mode="json")
        | {"stratigraphic_column_names": zone.stratigraphic_column_name}
        for zone in config.rms.zones
    ]
    return pa.Table.from_pylist(rows).drop(["stratigraphic_column_name"])
