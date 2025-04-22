from __future__ import annotations

from pathlib import Path
from typing import Final

from fmu.dataio._logging import null_logger
from fmu.dataio.export._base import SimpleExportBase

logger: Final = null_logger(__name__)

CONFIG_PATH = Path("../../fmuconfig/output/global_variables.yml")
"""Path to the global configuration file from the rms/model directory."""


class SimpleExportRMSBase(SimpleExportBase):
    """Base class for simple export classes intended for use in RMS."""

    def __init__(self) -> None:
        super().__init__(config_path=CONFIG_PATH)
