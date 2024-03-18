"""Module for DataIO metadata.

This contains the _MetaData class which collects and holds all relevant metadata
"""
# https://realpython.com/python-data-classes/#basic-data-classes

from __future__ import annotations

import datetime
import getpass
import os
import platform
from datetime import timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Final

from pydantic import AnyHttpUrl, TypeAdapter

from . import types
from ._definitions import SCHEMA, SOURCE, VERSION, FmuContext
from ._logging import null_logger
from ._utils import (
    drop_nones,
    export_file_compute_checksum_md5,
    glue_metadata_preprocessed,
    read_metadata_from_file,
)
from .datastructure._internal import internal
from .datastructure.meta import meta
from .providers._filedata import FileDataProvider
from .providers._fmu import FmuProvider
from .providers._objectdata import objectdata_provider_factory
from .version import __version__

if TYPE_CHECKING:
    from .dataio import ExportData
    from .providers._objectdata_base import ObjectDataProvider

logger: Final = null_logger(__name__)


def generate_meta_tracklog() -> meta.TracklogEvent:
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
    object: types.Inferrable,
    dataio: ExportData,
    meta_existing: dict | None = None,
) -> ObjectDataProvider:
    """Analyze the actual object together with input settings.

    This will provide input to the ``data`` block of the metas but has also
    valuable settings which are needed when providing filedata etc.

    Hence this must be ran early or first.
    """
    objdata = objectdata_provider_factory(object, dataio, meta_existing)
    objdata.derive_metadata()
    return objdata


def _get_filedata_provider(
    dataio: ExportData, objdata: ObjectDataProvider, fmudata: FmuProvider | None
) -> FileDataProvider:
    filedata = FileDataProvider(
        dataio=dataio,
        objdata=objdata,
        rootpath=dataio._rootpath,  # has been updated to case_path if fmurun
        itername=fmudata.get_iter_name() if fmudata else "",
        realname=fmudata.get_real_name() if fmudata else "",
    )
    filedata.derive_filedata()
    return filedata


def _compute_md5(
    dataio: ExportData, objdata: ObjectDataProvider, object: types.Inferrable
) -> str:
    """Return the file block in the metadata."""

    if not objdata.extension.startswith("."):
        raise ValueError("An extension must start with '.'")
    with NamedTemporaryFile(
        buffering=0,
        suffix=objdata.extension,
    ) as tf:
        logger.info("Compute MD5 sum for tmp file...: %s", tf.name)
        return export_file_compute_checksum_md5(
            obj=object,
            filename=Path(tf.name),
            flag=dataio._usefmtflag,
        )


def _reuse_existing_metadata(
    dataio: ExportData, meta: dict, meta_existing: dict
) -> dict:
    """Perform a merge procedure if the key `reuse_metadata_rule` is active."""
    if dataio.reuse_metadata_rule == "preprocessed":
        return glue_metadata_preprocessed(meta_existing, meta.copy())
    raise ValueError(
        f"The reuse_metadata_rule {dataio.reuse_metadata_rule} is not " "supported."
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

    meta_existing = {}
    if isinstance(obj, (str, Path)) and dataio.reuse_metadata_rule:
        logger.info("Partially reuse existing metadata from %s", obj)
        meta_existing = read_metadata_from_file(obj)

    objdata = _get_objectdata_provider(obj, dataio, meta_existing)
    filedata = _get_filedata_provider(dataio, objdata, fmudata)

    checksum_md5 = _compute_md5(dataio, objdata, obj) if compute_md5 else None

    datameta = internal.DataMetaSchema(
        schema_=TypeAdapter(AnyHttpUrl).validate_strings(SCHEMA),  # type: ignore[call-arg]
        version=VERSION,
        source=SOURCE,
        class_=objdata.classname,
        masterdata=dataio.config.get("masterdata"),
        fmu=fmudata.get_metadata() if fmudata else None,
        access=dataio.config.get("access"),
        data=objdata.metadata,
        file=meta.File(
            absolute_path=filedata.absolute_path,
            relative_path=filedata.relative_path,
            checksum_md5=checksum_md5,
            relative_path_symlink=filedata.relative_path_symlink,
            absolute_path_symlink=filedata.absolute_path_symlink,
        ),
        tracklog=generate_meta_tracklog(),
        display=meta.Display(name=dataio.display_name or objdata.name),
        preprocessed=internal.PreprocessedInfo(
            name=dataio.name,
            tagname=dataio.tagname,
            subfolder=dataio.subfolder,
        )
        if dataio.fmu_context == FmuContext.PREPROCESSED
        else None,
    ).model_dump(mode="json", exclude_none=True, by_alias=True)

    if skip_null:
        datameta = drop_nones(datameta)

    if dataio.reuse_metadata_rule:
        return _reuse_existing_metadata(dataio, datameta, meta_existing)

    return datameta
