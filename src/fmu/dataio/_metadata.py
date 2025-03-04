"""
This module contains models used to output the metadata that sit beside the exported
data.

It contains internal data structures that are designed to depend on external modules,
but not the other way around. This design ensures modularity and flexibility, allowing
external modules to be potentially separated into their own repositories without
dependencies on the internals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, List, Literal, Optional, Union

from pydantic import Field

from ._logging import null_logger
from ._models.fmu_results import data, fields
from ._models.fmu_results.enums import FMUClass
from ._models.fmu_results.fmu_results import (
    CaseMetadata,
    ObjectMetadata,
)
from ._models.fmu_results.global_configuration import GlobalConfiguration
from ._models.fmu_results.standard_result import StandardResult
from .exceptions import InvalidMetadataError
from .providers._filedata import FileDataProvider
from .providers.objectdata._base import UnsetData
from .providers.objectdata._provider import objectdata_provider_factory

if TYPE_CHECKING:
    from . import types
    from .dataio import ExportData
    from .providers._fmu import FmuProvider
    from .providers.objectdata._base import ObjectDataProvider

logger: Final = null_logger(__name__)


class ObjectMetadataExport(ObjectMetadata, populate_by_name=True):
    """Wraps the schema ObjectMetadata, adjusting some values to optional for pragmatic
    purposes when exporting metadata."""

    # These type ignores are for making the field optional
    fmu: Optional[fields.FMU]  # type: ignore
    access: Optional[fields.SsdlAccess]  # type: ignore
    masterdata: Optional[fields.Masterdata]  # type: ignore
    # !! Keep UnsetData first in this union
    data: Union[UnsetData, data.AnyData]  # type: ignore
    preprocessed: Optional[bool] = Field(alias="_preprocessed", default=None)


class CaseMetadataExport(CaseMetadata, populate_by_name=True):
    """Adds the optional description field for backward compatibility."""

    class_: Literal[FMUClass.case] = Field(
        default=FMUClass.case, alias="class", title="metadata_class"
    )
    description: Optional[List[str]] = Field(default=None)


def _get_meta_filedata(
    dataio: ExportData,
    obj: types.Inferrable,
    objdata: ObjectDataProvider,
    fmudata: FmuProvider | None,
) -> fields.File:
    """Derive metadata for the file."""
    return FileDataProvider(
        dataio=dataio,
        objdata=objdata,
        runpath=fmudata.get_runpath() if fmudata else None,
        obj=obj,
    ).get_metadata()


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
    obj: types.Inferrable,
    dataio: ExportData,
    fmudata: FmuProvider | None = None,
    standard_result: StandardResult | None = None,
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

    objdata = objectdata_provider_factory(obj, dataio, standard_result)

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
        file=_get_meta_filedata(dataio, obj, objdata, fmudata),
        tracklog=fields.Tracklog.initialize(),
        display=_get_meta_display(dataio, objdata),
        preprocessed=dataio.preprocessed,
    )
