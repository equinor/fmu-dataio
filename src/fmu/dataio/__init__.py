"""Top-level package for fmu-dataio"""

import logging
from fmu.dataio.dataio import ExportData

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


logging_level = logging.CRITICAL
logging_fmt = "%(asctime)s | %(name)s | %(levelname)s|> %(message)s"
try:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    root_handler = root_logger.handlers[0]
    root_handler.setFormatter(logging.Formatter(logging_fmt))
except IndexError:
    logging.basicConfig(level=logging_level, format=logging_fmt)
