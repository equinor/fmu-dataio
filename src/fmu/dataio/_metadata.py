"""
This module contains models used to output the metadata that sit beside the exported
data.

It contains internal data structures that are designed to depend on external modules,
but not the other way around. This design ensures modularity and flexibility, allowing
external modules to be potentially separated into their own repositories without
dependencies on the internals.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from pydantic import Field

from fmu.datamodels.common.access import Asset, Ssdl, SsdlAccess
from fmu.datamodels.common.masterdata import Masterdata
from fmu.datamodels.common.tracklog import Tracklog
from fmu.datamodels.fmu_results import data, fields
from fmu.datamodels.fmu_results.fmu_results import ObjectMetadata
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._export_config import ExportConfig
from ._logging import null_logger
from .exceptions import InvalidMetadataError
from .providers._filedata import FileDataProvider, SharePathConstructor
from .providers._fmu import FmuProvider
from .providers.objectdata._base import UnsetData
from .providers.objectdata._provider import (
    ObjectDataProvider,
    objectdata_provider_factory,
)
from .version import __version__

if TYPE_CHECKING:
    from ._export_config import ExportConfig
    from ._runcontext import RunContext
    from .providers.objectdata._base import ObjectDataProvider
    from .types import Inferrable

logger: Final = null_logger(__name__)


class ObjectMetadataExport(ObjectMetadata, populate_by_name=True):
    """Wraps the schema ObjectMetadata, adjusting some values to optional for pragmatic
    purposes when exporting metadata."""

    # These type ignores are for making the field optional
    fmu: fields.FMU | None  # type: ignore
    access: SsdlAccess | None  # type: ignore
    masterdata: Masterdata | None  # type: ignore
    # !! Keep UnsetData first in this union
    data: UnsetData | data.AnyData  # type: ignore
    preprocessed: bool | None = Field(alias="_preprocessed", default=None)


def _get_meta_filedata(
    runcontext: RunContext,
    objdata: ObjectDataProvider,
    share_path: Path,
) -> fields.File:
    """Derive metadata for the file."""
    return FileDataProvider(runcontext, objdata, share_path).get_metadata()


def _get_meta_fmu(fmudata: FmuProvider) -> fields.FMU | None:
    try:
        return fmudata.get_metadata()
    except InvalidMetadataError:
        return None


def _get_meta_access(export_config: ExportConfig) -> SsdlAccess:
    return SsdlAccess(
        asset=(
            export_config.config.access.asset
            if isinstance(export_config.config, GlobalConfiguration)
            else Asset(name="")
        ),
        classification=export_config.classification,
        ssdl=Ssdl(
            access_level=export_config.classification,
            rep_include=export_config.rep_include,
        ),
    )


def _get_meta_display(
    export_config: ExportConfig, objdata: ObjectDataProvider
) -> fields.Display:
    return fields.Display(name=export_config.display.name or objdata.name)


def generate_export_metadata(
    objdata: ObjectDataProvider, export_config: ExportConfig
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
    share_path = SharePathConstructor(export_config, objdata).get_share_path()
    fmudata = (
        FmuProvider(
            runcontext=export_config.runcontext,
            model=(export_config.config.model if export_config.config else None),
            workflow=export_config.workflow,
            share_path=share_path,
        )
        if export_config.runcontext.inside_fmu
        else None
    )

    return ObjectMetadataExport(  # type: ignore[call-arg]
        class_=objdata.classname,
        fmu=_get_meta_fmu(fmudata) if fmudata else None,
        masterdata=(
            export_config.config.masterdata
            if isinstance(export_config.config, GlobalConfiguration)
            else None
        ),
        access=_get_meta_access(export_config),
        data=objdata.get_metadata(),
        file=_get_meta_filedata(export_config.runcontext, objdata, share_path),
        tracklog=Tracklog.initialize(__version__),
        display=_get_meta_display(export_config, objdata),
        preprocessed=export_config.preprocessed,
    )


def generate_metadata(export_config: ExportConfig, obj: Inferrable) -> dict[str, Any]:
    """Generate metadata without exporting."""
    objdata = objectdata_provider_factory(obj, export_config)
    return _generate_metadata(export_config, objdata)


def _generate_metadata(
    export_config: ExportConfig, objdata: ObjectDataProvider
) -> dict[str, Any]:
    """Generate metadata dict from object data provider."""
    return generate_export_metadata(
        objdata=objdata,
        export_config=export_config,
    ).model_dump(mode="json", exclude_none=True, by_alias=True)
