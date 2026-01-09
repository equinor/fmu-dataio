from typing import Any

import pytest
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from fmu.dataio.export._base import SimpleExportBase


def test_validate_global_config_invalid(mock_global_config: dict[str, Any]) -> None:
    invalid_config = mock_global_config.copy()
    invalid_config.pop("masterdata")

    with pytest.raises(ValueError, match="valid config"):
        SimpleExportBase._validate_global_config(invalid_config)


def test_validate_global_config(mock_global_config: dict[str, Any]) -> None:
    config = SimpleExportBase._validate_global_config(mock_global_config)
    assert isinstance(config, GlobalConfiguration)
