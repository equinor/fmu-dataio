"""Module for DataIO metadata.

This contains the _MetaData class which collects and holds all relevant metadata
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pydantic import AnyHttpUrl, TypeAdapter

from ._definitions import SCHEMA, SOURCE, VERSION
from ._logging import null_logger
from ._model import fields, schema
from ._model.global_configuration import GlobalConfiguration
from .exceptions import InvalidMetadataError
from .providers._filedata import FileDataProvider
from .providers.objectdata._provider import objectdata_provider_factory

if TYPE_CHECKING:
    from . import types
    from .dataio import ExportData
    from .providers._fmu import FmuProvider
    from .providers.objectdata._base import ObjectDataProvider

logger: Final = null_logger(__name__)


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


def _get_meta_fmu(fmudata: FmuProvider) -> schema.InternalFMU | None:
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
) -> schema.InternalObjectMetadata:
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

    objdata = objectdata_provider_factory(obj, dataio)

    return schema.InternalObjectMetadata(
        schema_=TypeAdapter(AnyHttpUrl).validate_strings(SCHEMA),  # type: ignore[call-arg]
        version=VERSION,
        source=SOURCE,
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
