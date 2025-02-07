from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from fmu.dataio._models import FmuResults


def test_version_string_type(metadata_examples: dict[str, Any]) -> None:
    """Tests fmu.dataio.types.VerionStr"""
    example = deepcopy(metadata_examples["surface_depth.yml"])
    example["version"] = "1.2.a"
    with pytest.raises(ValidationError, match="String should match pattern"):
        FmuResults.model_validate(example)
    example["version"] = "1.2"
    with pytest.raises(ValidationError, match="String should match pattern"):
        FmuResults.model_validate(example)
