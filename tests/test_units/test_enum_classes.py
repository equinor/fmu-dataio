from __future__ import annotations

import pytest
from fmu.dataio._definitions import FmuContext


def test_fmu_context_validation() -> None:
    """Test the FmuContext enum class."""
    rel = FmuContext.get("realization")
    assert rel.name == "REALIZATION"

    with pytest.raises(KeyError, match="Invalid key"):
        FmuContext.get("invalid_context")

    valid_types = FmuContext.list_valid()
    assert list(valid_types.keys()) == [
        "REALIZATION",
        "CASE",
        "CASE_SYMLINK_REALIZATION",
        "PREPROCESSED",
        "NON_FMU",
    ]
