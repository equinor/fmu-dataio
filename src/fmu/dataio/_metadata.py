"""Module for DataIO metadata.

This contains the _MetaData class which collects and holds all relevant metadata
"""

# https://realpython.com/python-data-classes/#basic-data-classes

from __future__ import annotations

import datetime
import getpass
import os
import platform
from dataclasses import dataclass, field
from datetime import timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Final
from copy import deepcopy

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
from .datastructure.configuration import global_configuration
from .datastructure.meta import meta
from .providers._filedata import FileDataProvider
from .providers._fmu import FmuProvider
from .providers.objectdata._provider import objectdata_provider_factory
from .version import __version__

if TYPE_CHECKING:
    from .dataio import ExportData
    from .providers._objectdata_base import ObjectDataProvider

logger: Final = null_logger(__name__)


# Generic, being resused several places:


def default_meta_dollars() -> dict[str, str]:
    return internal.JsonSchemaMetadata(
        schema_=TypeAdapter(AnyHttpUrl).validate_strings(SCHEMA),  # type: ignore[call-arg]
        version=VERSION,
        source=SOURCE,
    ).model_dump(
        mode="json",
        by_alias=True,
    )


def generate_meta_tracklog() -> list[meta.TracklogEvent]:
    """Initialize the tracklog with the 'created' event only."""
    return [
        meta.TracklogEvent.model_construct(
            datetime=datetime.datetime.now(timezone.utc),
            event="created",
            user=meta.User.model_construct(id=getpass.getuser()),
            sysinfo=meta.SystemInformation.model_construct(
                fmu_dataio=meta.VersionInformation.model_construct(version=__version__),
                komodo=(
                    meta.VersionInformation.model_construct(version=kr)
                    if (kr := os.environ.get("KOMODO_RELEASE"))
                    else None
                ),
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


@dataclass
class MetaData:
    """Class for sampling, process and holding all metadata in an ExportData instance.

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
    * meta_access: dict with name of asset + security classification
    * meta_objectdata: the data block, may be complex
    * meta_display: dict of default display settings (experimental)

    """

    # input variables
    obj: types.Inferrable
    dataio: ExportData
    compute_md5: bool = True

    # storage state variables
    objdata: ObjectDataProvider | None = field(default=None, init=False)
    fmudata: FmuProvider | None = field(default=None, init=False)
    iter_name: str = field(default="", init=False)
    real_name: str = field(default="", init=False)

    meta_class: str = field(default="", init=False)
    meta_masterdata: dict = field(default_factory=dict, init=False)
    meta_objectdata: dict = field(default_factory=dict, init=False)
    meta_dollars: dict = field(default_factory=default_meta_dollars, init=False)
    meta_access: dict = field(default_factory=dict, init=False)
    meta_file: dict = field(default_factory=dict, init=False)
    meta_tracklog: list = field(default_factory=list, init=False)
    meta_fmu: dict = field(default_factory=dict, init=False)
    # temporary storage for preprocessed data:
    meta_xpreprocessed: dict = field(default_factory=dict, init=False)

    # relevant when ERT* fmu_context; same as rootpath in the ExportData class!:
    rootpath: str = field(default="", init=False)

    # if re-using existing metadata
    meta_existing: dict = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        logger.info("Initialize _MetaData instance.")

        # one special case is that obj is a file path.
        # In this case we read the existing metadata here and reuse parts
        if isinstance(self.obj, (str, Path)) and self.dataio._reuse_metadata:
            logger.info("Partially reuse existing metadata from %s", self.obj)
            self.meta_existing = read_metadata_from_file(self.obj)

        self.rootpath = str(self.dataio._rootpath.absolute())

    def _populate_meta_objectdata(self) -> None:
        """Analyze the actual object together with input settings.

        This will provide input to the ``data`` block of the metas but has also
        valuable settings which are needed when providing filedata etc.

        Hence this must be ran early or first.
        """
        self.objdata = objectdata_provider_factory(
            self.obj, self.dataio, self.meta_existing
        )
        self.objdata.derive_metadata()
        self.meta_objectdata = self.objdata.metadata

    def _populate_meta_fmu(self) -> None:
        """Populate the fmu block in the metadata.

        This block may be missing in case the client is not within a FMU run, e.g.
        it runs from RMS interactive

        The _FmuDataProvider is ran to provide this information
        """
        fmudata = FmuProvider(
            model=self.dataio.config.get("model", None),
            fmu_context=FmuContext.get(self.dataio.fmu_context),
            casepath_proposed=self.dataio.casepath or "",
            include_ertjobs=self.dataio.include_ertjobs,
            forced_realization=self.dataio.realization,
            workflow=self.dataio.workflow,
        )
        logger.info("FMU provider is %s", fmudata.get_provider())

        self.meta_fmu = fmudata.get_metadata()
        self.rootpath = fmudata.get_casepath()
        self.iter_name = fmudata.get_iter_name()
        self.real_name = fmudata.get_real_name()

        logger.debug("Rootpath is now %s", self.rootpath)

    def _populate_meta_file(self) -> None:
        """Populate the file block in the metadata.

        The file block also contains all needed info for doing the actual file export.

        It requires that the _ObjectDataProvider is ran first -> self.objdata

        - relative_path, seen from rootpath
        - absolute_path, as above but full path
        - checksum_md5, if required (a bit special treatment of this)

        In additional _optional_ symlink adresses
        - relative_path_symlink, seen from rootpath
        - absolute_path_symlink, as above but full path
        """

        assert self.objdata is not None

        fdata = FileDataProvider(
            self.dataio,
            self.objdata,
            Path(self.rootpath),
            self.iter_name,
            self.real_name,
        )
        fdata.derive_filedata()

        if self.compute_md5:
            if not self.objdata.extension.startswith("."):
                raise ValueError("A extension must start with '.'")
            with NamedTemporaryFile(
                buffering=0,
                suffix=self.objdata.extension,
            ) as tf:
                logger.info("Compute MD5 sum for tmp file...: %s", tf.name)
                checksum_md5 = export_file_compute_checksum_md5(
                    self.obj,
                    Path(tf.name),
                    flag=self.dataio._usefmtflag,
                )
        else:
            logger.info("Do not compute MD5 sum at this stage!")
            checksum_md5 = None

        self.meta_file = meta.File(
            absolute_path=fdata.absolute_path,
            relative_path=fdata.relative_path,
            checksum_md5=checksum_md5,
            relative_path_symlink=fdata.relative_path_symlink,
            absolute_path_symlink=fdata.absolute_path_symlink,
        ).model_dump(
            mode="json",
            exclude_none=True,
            by_alias=True,
        )

    def _populate_meta_class(self) -> None:
        """Get the general class which is a simple string."""
        assert self.objdata is not None
        self.meta_class = self.objdata.classname

    def _populate_meta_tracklog(self) -> None:
        """Create the tracklog metadata, which here assumes 'created' only."""
        self.meta_tracklog = [
            x.model_dump(mode="json", exclude_none=True, by_alias=True)
            for x in generate_meta_tracklog()
        ]

    def _populate_meta_masterdata(self) -> None:
        """Populate metadata from masterdata section in config."""
        self.meta_masterdata = self.dataio.config.get("masterdata", {})

    def _populate_meta_access(self) -> None:
        """Populate metadata overall from access section in config + allowed keys.

        The access block contains the following keys:
        access:
          asset: str
          ssdl:
            rep_include: [True/False]
            access_level: ["internal"/"restricted"] # to be deprecated
          classification: ["internal"/"restricted"]

        The "asset" field shall come from the config. This is static information.
        The "classification" and "rep_include" fields are dynamic. They can be set via
        input arguments. If not set, they will fall back to defaults from config.

        WIP: We are deprecating the 'access_ssdl' input argument, replacing it with the
        'rep_include' and 'classification' arguments. While 'access_ssdl' is deprecated,
        we still support it. Therefore, we must account for all possible weird
        combinations for a while.
        """

        # Will find "asset" no matter what the config looks like, which smells bad.
        # Reason is that we allow non-valid config (which we should not?)
        # access.asset always comes from config, never argument
        asset = self.dataio.config.get("access", {}).get("asset", None)
        classification = self._get_meta_access_classification()
        rep_include = self._get_meta_access_rep_include()

        m_access = {
            "asset": asset,
            "classification": classification,
            "ssdl": {
                "access_level": classification,
                "rep_include": rep_include,
            },
        }

        self.meta_access = (
            global_configuration.Access.model_validate(m_access).model_dump(
                mode="json", exclude_none=True
            )
            if self.dataio._config_is_valid
            else {}
        )

    def _get_meta_access_classification(self) -> str:
        classification = self.dataio.classification

        if classification is None:
            # fall back to config, which can be non-valid and non-existing
            # First try the access.classification directly
            classification = self.dataio.config.get("access", {}).get("classification")

        if classification is None:
            # then fall back to legacy access.ssdl.access_level
            classification = (
                self.dataio.config.get("access", {})
                .get("ssdl", {})
                .get("access_level", None)
            )

        if classification is None:
            # if none of the above works, then I don't know what to do...
            # I guess this will now be in the hands of Pydantic validation?
            pass

        return classification

    def _get_meta_access_rep_include(self) -> bool:
        rep_include = self.dataio.rep_include

        if rep_include is None:
            # fall back to config, which can be non-valid and non-existing
            rep_include = (
                self.dataio.config.get("access", {})
                .get("ssdl", {})
                .get("rep_include", None)
            )

        return rep_include

    def _populate_meta_display(self) -> None:
        """Populate the display block."""

        # display.name
        if self.dataio.display_name is not None:
            display_name = self.dataio.display_name
        else:
            assert self.objdata is not None
            display_name = self.objdata.name

        self.meta_display = {"name": display_name}

    def _populate_meta_xpreprocessed(self) -> None:
        """Populate a few necessary 'tmp' metadata needed for preprocessed data."""
        if self.dataio.fmu_context == FmuContext.PREPROCESSED:
            self.meta_xpreprocessed["name"] = self.dataio.name
            self.meta_xpreprocessed["tagname"] = self.dataio.tagname
            self.meta_xpreprocessed["subfolder"] = self.dataio.subfolder

    def _reuse_existing_metadata(self, meta: dict) -> dict:
        """Perform a merge procedure if input is a file i.e. `_reuse_metadata=True`"""
        if self.dataio._reuse_metadata:
            return glue_metadata_preprocessed(
                oldmeta=self.meta_existing, newmeta=meta.copy()
            )
        return meta

    def generate_export_metadata(
        self, skip_null: bool = True
    ) -> dict:  # TODO! -> skip_null?
        """Main function to generate the full metadata"""

        # populate order matters, in particular objectdata provides input to class/file
        self._populate_meta_masterdata()
        self._populate_meta_access()

        if self.dataio._fmurun:
            self._populate_meta_fmu()

        self._populate_meta_tracklog()
        self._populate_meta_objectdata()
        self._populate_meta_class()
        self._populate_meta_file()
        self._populate_meta_display()
        self._populate_meta_xpreprocessed()

        # glue together metadata, order is as legacy code (but will be screwed if reuse
        # of existing metadata...)
        meta = self.meta_dollars.copy()
        meta["tracklog"] = self.meta_tracklog
        meta["class"] = self.meta_class

        meta["fmu"] = self.meta_fmu
        meta["file"] = self.meta_file

        meta["data"] = self.meta_objectdata
        meta["display"] = self.meta_display

        meta["access"] = self.meta_access
        meta["masterdata"] = self.meta_masterdata

        if self.dataio.fmu_context == FmuContext.PREPROCESSED:
            meta["_preprocessed"] = self.meta_xpreprocessed

        if skip_null:
            meta = drop_nones(meta)

        return self._reuse_existing_metadata(meta)
