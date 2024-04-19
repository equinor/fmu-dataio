"""Module for DataIO metadata.

This contains the _MetaData class which collects and holds all relevant metadata
"""

from __future__ import annotations

import datetime
import getpass
import os
import platform
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pydantic import AnyHttpUrl, TypeAdapter

from . import types
from ._definitions import SCHEMA, SOURCE, VERSION, FmuContext
from ._logging import null_logger
from ._utils import (
    drop_nones,
    glue_metadata_preprocessed,
    read_metadata_from_file,
)
from .datastructure._internal import internal
from .datastructure.meta import meta
from .providers._filedata import FileDataProvider
from .providers._fmu import FmuProvider
from .providers.objectdata._provider import objectdata_provider_factory
from .version import __version__

if TYPE_CHECKING:
    from .dataio import ExportData
    from .providers.objectdata._base import ObjectDataProvider

logger: Final = null_logger(__name__)


def generate_meta_tracklog() -> list[meta.TracklogEvent]:
    """Initialize the tracklog with the 'created' event only."""
    return [
        meta.TracklogEvent.model_construct(
            datetime=datetime.datetime.now(timezone.utc),
            event="created",
            user=meta.User.model_construct(id=getpass.getuser()),
            sysinfo=meta.SystemInformation.model_construct(
                fmu_dataio=meta.VersionInformation.model_construct(version=__version__),
                komodo=meta.VersionInformation.model_construct(version=kr)
                if (kr := os.environ.get("KOMODO_RELEASE"))
                else None,
                operating_system=meta.SystemInformationOperatingSystem.model_construct(
                    hostname=platform.node(),
                    operating_system=platform.platform(),
                    release=platform.release(),
                    system=platform.system(),
                    version=platform.version(),
                ),
            ),
        )
    ]


def _get_objectdata_provider(
    obj: types.Inferrable, dataio: ExportData, meta_existing: dict | None = None
) -> ObjectDataProvider:
    """Derive metadata for the object. Reuse metadata if existing"""
    objdata = objectdata_provider_factory(obj, dataio, meta_existing)
    objdata.derive_metadata()
    return objdata


def _get_filedata_provider(
    dataio: ExportData,
    obj: types.Inferrable,
    objdata: ObjectDataProvider,
    fmudata: FmuProvider | None,
    compute_md5: bool,
) -> FileDataProvider:
    """Derive metadata for the file."""
    return FileDataProvider(
        dataio=dataio,
        objdata=objdata,
        runpath=fmudata.get_runpath() if fmudata else None,
        obj=obj,
        compute_md5=compute_md5,
    )


def _get_meta_objectdata(
    objdata: ObjectDataProvider,
) -> meta.content.AnyContent | internal.UnsetAnyContent:
    return (
        internal.UnsetAnyContent.model_validate(objdata.metadata)
        if objdata.metadata["content"] == "unset"
        else meta.content.AnyContent.model_validate(objdata.metadata)
    )


def _get_meta_access(dataio: ExportData) -> meta.SsdlAccess:
    return meta.SsdlAccess(
        asset=meta.Asset(
            name=dataio.config.get("access", {}).get("asset", {}).get("name", "")
        ),
        classification=dataio._classification,
        ssdl=meta.Ssdl(
            access_level=dataio._classification,
            rep_include=dataio._rep_include,
        ),
    )


def _get_meta_masterdata(masterdata: dict) -> meta.Masterdata:
    return meta.Masterdata.model_validate(masterdata)


def _get_meta_display(dataio: ExportData, objdata: ObjectDataProvider) -> meta.Display:
    return meta.Display(name=dataio.display_name or objdata.name)


def _get_meta_preprocessed_info(dataio: ExportData) -> internal.PreprocessedInfo:
    return internal.PreprocessedInfo(
        name=dataio.name,
        tagname=dataio.tagname,
        subfolder=dataio.subfolder,
    )


def generate_export_metadata(
    obj: types.Inferrable,
    dataio: ExportData,
    fmudata: FmuProvider | None = None,
    compute_md5: bool = True,
    skip_null: bool = True,
) -> dict:  # TODO! -> skip_null?
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

    meta_existing = None
    if isinstance(obj, (str, Path)) and dataio._reuse_metadata:
        logger.info("Partially reuse existing metadata from %s", obj)
        meta_existing = read_metadata_from_file(obj)

    objdata = _get_objectdata_provider(obj, dataio, meta_existing)
    filedata = _get_filedata_provider(dataio, obj, objdata, fmudata, compute_md5)

    masterdata = dataio.config.get("masterdata")

    metadata = internal.DataClassMeta(
        schema_=TypeAdapter(AnyHttpUrl).validate_strings(SCHEMA),  # type: ignore[call-arg]
        version=VERSION,
        source=SOURCE,
        class_=objdata.classname,
        fmu=fmudata.get_metadata() if fmudata else None,
        masterdata=_get_meta_masterdata(masterdata) if masterdata else None,
        access=_get_meta_access(dataio),
        data=_get_meta_objectdata(objdata),
        file=filedata.get_metadata(),
        tracklog=generate_meta_tracklog(),
        display=_get_meta_display(dataio, objdata),
        preprocessed=_get_meta_preprocessed_info(dataio)
        if dataio.fmu_context == FmuContext.PREPROCESSED
        else None,
    ).model_dump(mode="json", exclude_none=True, by_alias=True)

    if skip_null:
        metadata = drop_nones(metadata)

    return (
        metadata
        if not meta_existing
        else glue_metadata_preprocessed(oldmeta=meta_existing, newmeta=metadata.copy())
    )
