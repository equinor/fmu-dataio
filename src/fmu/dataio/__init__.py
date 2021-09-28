"""Top-level package for fmu-dataio"""
# noqa

import logging

from fmu.dataio.dataio import ExportData  # noqa  # type: ignore
from fmu.dataio.dataio import InitializeCase  # noqa  # type: ignore

try:
    from .version import version

    __version__ = version
except ImportError:
    __version__ = "0.0.0"


LOGGING_LEVEL = logging.CRITICAL

LFMT = "%(levelname)8s (%(relativeCreated)6.0fms) %(name)37s [%(funcName)42s()] "
LFMT += "%(lineno)4d >>   %(message)s"
try:
    root_logger = logging.getLogger()
    root_logger.setLevel(LOGGING_LEVEL)
    root_handler = root_logger.handlers[0]
    root_handler.setFormatter(logging.Formatter(LFMT))
except IndexError:
    logging.basicConfig(level=LOGGING_LEVEL, format=LFMT)
