from pathlib import Path

import pyarrow as pa
from fmu.datamodels.standard_results.model_stratigraphy_horizons import (
    ModelStratigraphyHorizonsResult,
)
from fmu.datamodels.standard_results.model_stratigraphy_zones import (
    ModelStratigraphyZonesResult,
)
from fmu.settings._drogon import create_drogon_fmu_dir

from fmu.dataio._workflows.case._model_stratigraphy import (
    get_model_stratigraphy_horizons_table,
    get_model_stratigraphy_zones_table,
)


def test_get_model_stratigraphy_horizons_table(tmp_path: Path) -> None:
    fmu_dir = create_drogon_fmu_dir(tmp_path)

    table = get_model_stratigraphy_horizons_table(fmu_dir)

    assert isinstance(table, pa.Table)
    assert table.column_names == ["name", "type", "stratigraphic_order"]
    assert table["stratigraphic_order"].to_pylist() == list(range(len(table)))
    ModelStratigraphyHorizonsResult.model_validate(table.to_pylist())


def test_get_model_stratigraphy_zones_table(tmp_path: Path) -> None:
    fmu_dir = create_drogon_fmu_dir(tmp_path)

    table = get_model_stratigraphy_zones_table(fmu_dir)

    assert isinstance(table, pa.Table)
    assert table.column_names == [
        "name",
        "top_horizon_name",
        "base_horizon_name",
        "stratigraphic_column_names",
    ]
    ModelStratigraphyZonesResult.model_validate(table.to_pylist())


def test_model_stratigraphy_tables_return_none_without_rms_data(
    tmp_path: Path,
) -> None:
    fmu_dir = create_drogon_fmu_dir(tmp_path)
    fmu_dir.config.set("rms", None)

    assert get_model_stratigraphy_horizons_table(fmu_dir) is None
    assert get_model_stratigraphy_zones_table(fmu_dir) is None
