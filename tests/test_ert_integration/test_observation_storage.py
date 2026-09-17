"""Check conversion of observation tables produced by ERT storage."""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import get_args

import jsonschema
import pytest
from ert.config import ErtConfig, RFTConfig
from ert.storage import Ensemble, open_storage
from fmu.datamodels import (
    ErtObservationsBreakthroughResult,
    ErtObservationsBreakthroughSchema,
    ErtObservationsRftResult,
    ErtObservationsRftSchema,
    ErtObservationsSummaryResult,
    ErtObservationsSummarySchema,
)

from fmu.dataio._workflows.case._observations import get_ert_observations_table

from .ert_config_utils import (
    add_breakthrough_observations,
    add_rft_observations,
    add_summary_observations,
)


@pytest.fixture
def observation_ensemble(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Ensemble]:
    """Create stored observations through ERT's public APIs."""
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "observations.ert"
    config_path.write_text(
        "NUM_REALIZATIONS 1\nECLBASE ECLIPSE_%d\nOBS_CONFIG observations\n",
        encoding="utf-8",
    )
    add_summary_observations(config_path)
    add_breakthrough_observations(config_path)
    add_rft_observations(config_path)
    config = ErtConfig.from_file(str(config_path))

    with open_storage(tmp_path / "storage", "w") as storage:
        experiment = storage.create_experiment(
            experiment_config={
                "observations": [
                    observation.model_dump(mode="json")
                    for observation in config.observation_declarations
                ],
                "shape_registry": config.shape_registry.model_dump(mode="json"),
                # ERT 23 needs a response configuration to store RFT observations.
                "response_configuration": [
                    RFTConfig(input_files=["ECLIPSE_%d"]).model_dump(mode="json")
                ],
            },
        )
        assert set(experiment.observations) == {"summary", "breakthrough", "rft"}
        yield experiment.create_ensemble(ensemble_size=1, name="observations")


def test_stored_rft_observations(observation_ensemble: Ensemble) -> None:
    """Stored RFT observations retain their values and satisfy the RFT schema."""
    table = get_ert_observations_table(observation_ensemble, "rft")
    assert table is not None
    row_model = get_args(ErtObservationsRftResult.model_fields["root"].annotation)[0]
    assert set(table.column_names) == set(row_model.model_fields)
    rows = table.to_pylist()

    assert rows == [
        {
            "response_key": "R_A6:2018-01-01:PRESSURE",
            "well": "R_A6",
            "date": "2018-01-01",
            "tvd": 8400.0,
            "md": None,
            "zone": "ZONE1",
            "observation_value": 3800.0,
            "observation_error": 30.5,
            "east": 9500.0,
            "north": 10500.5,
            "property": "PRESSURE",
        }
    ]
    jsonschema.validate(instance=rows, schema=ErtObservationsRftSchema.dump())


def test_stored_summary_observations(observation_ensemble: Ensemble) -> None:
    """Stored summary observations retain their values and satisfy the schema."""
    table = get_ert_observations_table(observation_ensemble, "summary")
    assert table is not None
    root_field = ErtObservationsSummaryResult.model_fields["root"]
    row_model = get_args(root_field.annotation)[0]
    assert set(table.column_names) == set(row_model.model_fields)
    rows = table.to_pylist()

    assert len(rows) == 2
    assert [row["response_key"] for row in rows] == ["FOPR", "FGPT"]
    assert [row["time"] for row in rows] == [
        datetime(2020, 1, 1),
        datetime(2025, 1, 1),
    ]
    assert [row["observation_value"] for row in rows] == pytest.approx([0.9, 100.5])
    assert [row["observation_error"] for row in rows] == pytest.approx([0.05, 10.0])
    for row in rows:
        assert row["east"] is None
        assert row["north"] is None
        row["time"] = row["time"].isoformat()

    jsonschema.validate(instance=rows, schema=ErtObservationsSummarySchema.dump())


def test_stored_breakthrough_observations(observation_ensemble: Ensemble) -> None:
    """Stored breakthrough observations retain their values and satisfy the schema."""
    table = get_ert_observations_table(observation_ensemble, "breakthrough")
    assert table is not None
    root_field = ErtObservationsBreakthroughResult.model_fields["root"]
    row_model = get_args(root_field.annotation)[0]
    assert set(table.column_names) == set(row_model.model_fields)
    rows = table.to_pylist()

    assert len(rows) == 2
    assert [row["response_key"] for row in rows] == [
        "BREAKTHROUGH:FOPR",
        "BREAKTHROUGH:FGPT",
    ]
    assert [row["time"] for row in rows] == [
        datetime(2020, 1, 1),
        datetime(2025, 1, 1),
    ]
    assert [row["observation_value"] for row in rows] == [0.0, 0.0]
    assert [row["observation_error"] for row in rows] == pytest.approx([0.05, 10.0])
    assert [row["threshold"] for row in rows] == [0.5, 50.0]
    for row in rows:
        assert row["east"] is None
        assert row["north"] is None
        row["time"] = row["time"].isoformat()

    jsonschema.validate(instance=rows, schema=ErtObservationsBreakthroughSchema.dump())
