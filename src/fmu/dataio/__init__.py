"""Top-level package for fmu-dataio"""
# noqa

import logging
from fmu.dataio.dataio import ExportData  # noqa  # type: ignore

# try:
#     import roxar  # noqa

#     ROXAR = True
# except ImportError:
#     ROXAR = False

# if not ROXAR:

#     from .rms import volumetrics  # noqa

#     from .sensitivities import DesignMatrix  # noqa
#     from .sensitivities import summarize_design  # noqa
#     from .sensitivities import calc_tornadoinput  # noqa
#     from .sensitivities import excel2dict_design  # noqa

try:
    from .version import version

    __version__ = version
except ImportError:
    __version__ = "0.0.0"


LOGGING_LEVEL = logging.CRITICAL
LOGGING_FMT = "%(asctime)s | %(name)s | %(levelname)s|> %(message)s"
try:
    root_logger = logging.getLogger()
    root_logger.setLevel(LOGGING_LEVEL)
    root_handler = root_logger.handlers[0]
    root_handler.setFormatter(logging.Formatter(LOGGING_FMT))
except IndexError:
    logging.basicConfig(level=LOGGING_LEVEL, format=LOGGING_FMT)
