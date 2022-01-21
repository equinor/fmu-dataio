"""Top-level package for fmu-dataio"""
# noqa

from fmu.dataio.dataio import ExportData  # noqa  # type: ignore
from fmu.dataio.dataio import InitializeCase  # noqa  # type: ignore

try:
    from .version import version

    __version__ = version
except ImportError:
    __version__ = "0.0.0"
