"""
This module contains models used to output the metadata that sit beside the exported
data.

It contains internal data structures that are designed to depend on external modules,
but not the other way around. This design ensures modularity and flexibility, allowing
external modules to be potentially separated into their own repositories without
dependencies on the internals.
"""

from __future__ import annotations

from typing import Any, Final

from fmu.dataio._export import ExportConfig, ObjectMetadataExport
from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import InvalidMetadataError
from fmu.dataio.types import ExportableData
from fmu.dataio.version import __version__
from fmu.datamodels import Asset, Ssdl, SsdlAccess, Tracklog
from fmu.datamodels.fmu_results import fields
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._filedata import FileDataProvider, SharePathConstructor
from ._fmu import FmuProvider
from .objectdata import ObjectDataProvider, objectdata_provider_factory

logger: Final = null_logger(__name__)


def generate_export_metadata(
    objdata: ObjectDataProvider, export_config: ExportConfig
) -> ObjectMetadataExport:
    """
    Generates metadata for the object being exported.

    Metadata about the object is gathered from the object data provider passed to this
    function. Additional metadata comes from several sources created in this function
    call:

    - SharePathConstruct: Resolves the filepath where data will be exported to.
    - FmuProvider: Gathers data about the current FMU and run context (Ert environment
          variables, whether we're running in RMS, etc.)
    - FileDataProvider: Derives file-level metadata from the run context and share path.

    Arguments:
        objdata: Provides metadata about the object itself.
        export_config: Configuration being used to export the object.

    Returns:
        Pydantic model containing the complete metadata that will be exported.
    """
    share_path = SharePathConstructor(export_config, objdata).get_share_path()
    ctx = export_config.runcontext
    config = export_config.config
    global_config = config if isinstance(config, GlobalConfiguration) else None

    return ObjectMetadataExport(  # type: ignore[call-arg]
        class_=objdata.classname,
        fmu=_build_fmu_metadata(export_config, share_path),
        masterdata=global_config.masterdata if global_config else None,
        access=SsdlAccess(
            asset=global_config.access.asset if global_config else Asset(name=""),
            classification=export_config.classification,
            ssdl=Ssdl(
                access_level=export_config.classification,
                rep_include=export_config.rep_include,
            ),
        ),
        data=objdata.get_metadata(),
        file=FileDataProvider(ctx, objdata, share_path).get_metadata(),
        tracklog=Tracklog.initialize(__version__, export_config.tracklog_source),
        display=fields.Display(name=export_config.display.name or objdata.name),
        preprocessed=export_config.preprocessed,
    )


def generate_metadata(
    export_config: ExportConfig, obj: ExportableData
) -> dict[str, Any]:
    """Generate metadata without exporting."""
    objdata = objectdata_provider_factory(obj, export_config)
    return _generate_metadata(export_config, objdata)


def _generate_metadata(
    export_config: ExportConfig, objdata: ObjectDataProvider
) -> dict[str, Any]:
    """Generate metadata without exporting."""
    return generate_export_metadata(
        objdata=objdata,
        export_config=export_config,
    ).model_dump(mode="json", exclude_none=True, by_alias=True)


def _build_fmu_metadata(
    export_config: ExportConfig,
    share_path: fields.Path,
) -> fields.FMU | None:
    ctx = export_config.runcontext
    if not ctx.inside_fmu:
        return None

    provider = FmuProvider(
        runcontext=ctx,
        model=export_config.config.model if export_config.config else None,
        workflow=export_config.workflow,
        share_path=share_path,
    )
    try:
        return provider.get_metadata()
    except InvalidMetadataError:
        return None
