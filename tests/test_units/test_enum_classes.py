from __future__ import annotations

import pytest
from fmu.dataio._definitions import FmuContext


def test_fmu_context_validation() -> None:
    """Test the FmuContext enum class."""
    rel = FmuContext("realization")
    assert rel.name == "REALIZATION"

    with pytest.raises(ValueError, match="Invalid FmuContext value='invalid_context'"):
        FmuContext("invalid_context")

    assert FmuContext.list_valid_values() == [
        "realization",
        "case",
        "preprocessed",
        "non-fmu",
    ]
