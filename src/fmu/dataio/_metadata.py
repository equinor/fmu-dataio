"""
This module contains models used to output the metadata that sit beside the exported
data.

It contains internal data structures that are designed to depend on external modules,
but not the other way around. This design ensures modularity and flexibility, allowing
external modules to be potentially separated into their own repositories without
dependencies on the internals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pydantic import Field

from fmu.dataio.version import __version__
from fmu.datamodels.fmu_results import data, fields
from fmu.datamodels.fmu_results.fmu_results import (
    ObjectMetadata,
)
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._logging import null_logger
from .exceptions import InvalidMetadataError
from .providers._filedata import FileDataProvider
from .providers.objectdata._base import UnsetData

if TYPE_CHECKING:
    from ._runcontext import RunContext
    from .dataio import ExportData
    from .providers._fmu import FmuProvider
    from .providers.objectdata._base import ObjectDataProvider

logger: Final = null_logger(__name__)


class ObjectMetadataExport(ObjectMetadata, populate_by_name=True):
    """Wraps the schema ObjectMetadata, adjusting some values to optional for pragmatic
    purposes when exporting metadata."""

    # These type ignores are for making the field optional
    fmu: fields.FMU | None  # type: ignore
    access: fields.SsdlAccess | None  # type: ignore
    masterdata: fields.Masterdata | None  # type: ignore
    # !! Keep UnsetData first in this union
    data: UnsetData | data.AnyData  # type: ignore
    preprocessed: bool | None = Field(alias="_preprocessed", default=None)


def _get_meta_filedata(
    runcontext: RunContext, objdata: ObjectDataProvider
) -> fields.File:
    """Derive metadata for the file."""
    return FileDataProvider(runcontext, objdata).get_metadata()


def _get_meta_fmu(fmudata: FmuProvider) -> fields.FMU | None:
    try:
        return fmudata.get_metadata()
    except InvalidMetadataError:
        return None


def _get_meta_access(dataio: ExportData) -> fields.SsdlAccess:
    return fields.SsdlAccess(
        asset=(
            dataio.config.access.asset
            if isinstance(dataio.config, GlobalConfiguration)
            else fields.Asset(name="")
        ),
        classification=dataio._classification,
        ssdl=fields.Ssdl(
            access_level=dataio._classification,
            rep_include=dataio._rep_include,
        ),
    )


def _get_meta_display(
    dataio: ExportData, objdata: ObjectDataProvider
) -> fields.Display:
    return fields.Display(name=dataio.display_name or objdata.name)


def generate_export_metadata(
    objdata: ObjectDataProvider,
    dataio: ExportData,
    fmudata: FmuProvider | None = None,
) -> ObjectMetadataExport:
    """
    Main function to generate the full metadata

    Metadata has basically these different providers:

    * The FmuProvider, which is typically ERT, which provides a kind of an
      environment. The FmuProvider may also be legally missing, e.g. when
      running interactive RMS project

    * The User data, which is a mix of global variables and user set keys

    * The data object itself ie. ObjectDataProvider

    Then, metadata are stored as:

    * meta_dollars: holding 'system' state: $schema, version, source
    * meta_class: a simple string
    * meta_tracklog: dict of events (datdtime, user)
    * meta_fmu: nested dict of model, case, etc (complex)
    * meta_file: dict of paths and checksums
    * meta_masterdata: dict of (currently) smda masterdata
    * meta_access: dict with name of field + access rules
    * meta_objectdata: the data block, may be complex
    * meta_display: dict of default display settings (experimental)

    """

    return ObjectMetadataExport(  # type: ignore[call-arg]
        class_=objdata.classname,
        fmu=_get_meta_fmu(fmudata) if fmudata else None,
        masterdata=(
            dataio.config.masterdata
            if isinstance(dataio.config, GlobalConfiguration)
            else None
        ),
        access=_get_meta_access(dataio),
        data=objdata.get_metadata(),
        file=_get_meta_filedata(dataio._runcontext, objdata),
        tracklog=fields.Tracklog.initialize(__version__),
        display=_get_meta_display(dataio, objdata),
        preprocessed=dataio.preprocessed,
    )
