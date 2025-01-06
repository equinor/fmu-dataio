"""Handle rmsapi or roxar (deprecated version of rmsapi); only present inside RMS"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from fmu.dataio._logging import null_logger

_logger = null_logger(__name__)


def import_rms_package() -> tuple[Any, Any]:
    """
    Attempts to import the 'rmsapi' package first. If 'rmsapi' is not available,
    it attempts to import the 'roxar' package while suppressing deprecation warnings.
    Returns a dictionary with the imported modules or raises ImportError if neither
    is available.
    """
    try:
        import rmsapi
        from rmsapi import jobs

    except ImportError:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", category=DeprecationWarning, module="roxar"
                )
                import roxar as rmsapi
                from roxar import jobs

        except ImportError as e:
            raise ImportError(
                "Neither 'roxar' nor 'rmsapi' are available. You have to be inside "
                "RMS to use this function."
            ) from e

    return (rmsapi, jobs)


if TYPE_CHECKING:
    import rmsapi
    import rmsapi.jobs

    _logger.debug("Importing both %s and %s", rmsapi, rmsapi.jobs)
