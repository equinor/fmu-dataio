from typing import Any

import pytest
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from fmu.dataio.export._base import SimpleExportBase


def test_validate_global_config_invalid(globalconfig1: dict[str, Any]) -> None:
    invalid_config = globalconfig1.copy()
    invalid_config.pop("masterdata")

    with pytest.raises(ValueError, match="valid config"):
        SimpleExportBase._validate_global_config(invalid_config)


def test_validate_global_config(globalconfig1: dict[str, Any]) -> None:
    config = SimpleExportBase._validate_global_config(globalconfig1)
    assert isinstance(config, GlobalConfiguration)
