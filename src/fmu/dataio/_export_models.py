"""This module contains classes used when data is being exported from the object data
provider.

Mostly these classes are here to maintain backward compatibility while a deprecation
period is ongoing.
"""

from __future__ import annotations

import warnings
from typing import Final, Literal

from pydantic import (
    Field,
    model_validator,
)

from fmu.dataio._logging import null_logger
from fmu.datamodels.fmu_results import data, enums

logger: Final = null_logger(__name__)


class AllowedContentSeismic(data.Seismic):
    # Deprecated
    offset: str | None = Field(default=None)

    @model_validator(mode="after")
    def _check_depreciated(self) -> AllowedContentSeismic:
        if self.offset is not None:
            warnings.warn(
                "Content seismic.offset is deprecated. "
                "Please use seismic.stacking_offset insted.",
                DeprecationWarning,
            )
            self.stacking_offset, self.offset = self.offset, None
        return self


class UnsetData(data.Data):
    content: Literal["unset"]  # type: ignore

    @model_validator(mode="after")
    def _deprecation_warning(self) -> UnsetData:
        valid_contents = [m.value for m in enums.Content]
        warnings.warn(
            "The <content> is not provided which will produce invalid metadata. "
            "In the future 'content' will be required explicitly! "
            f"\n\nValid contents are: {', '.join(valid_contents)} "
            "\n\nThis list can be extended upon request and need.",
            FutureWarning,
        )
        return self
