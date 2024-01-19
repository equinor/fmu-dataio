"""Module for DataIO metadata.

This contains the _MetaData class which collects and holds all relevant metadata
"""
# https://realpython.com/python-data-classes/#basic-data-classes

from __future__ import annotations

import datetime
import getpass
from dataclasses import dataclass, field
from datetime import timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Final
from warnings import warn

from fmu import dataio
from fmu.dataio._definitions import SCHEMA, SOURCE, VERSION
from fmu.dataio._filedata_provider import _FileDataProvider
from fmu.dataio._fmu_provider import _FmuProvider
from fmu.dataio._objectdata_provider import _ObjectDataProvider
from fmu.dataio._utils import (
    drop_nones,
    export_file_compute_checksum_md5,
    glue_metadata_preprocessed,
    read_metadata,
    read_named_envvar,
)

from ._logging import null_logger

logger: Final = null_logger(__name__)


class ConfigurationError(ValueError):
    pass


# Generic, being resused several places:


def default_meta_dollars() -> dict:
    dollars = {}
    dollars["$schema"] = SCHEMA
    dollars["version"] = VERSION
    dollars["source"] = SOURCE
    return dollars


def generate_meta_tracklog() -> list[dict]:
    """Initialize the tracklog with the 'created' event only."""

    dtime = datetime.datetime.now(timezone.utc).isoformat()
    user = getpass.getuser()
    sysinfo = {
        "fmu-dataio": {"version": dataio.__version__},
    }
    _kmd = read_named_envvar("KOMODO_RELEASE")
    if _kmd is not None:
        sysinfo["komodo"] = {"version": _kmd}

    return [
        {
            "datetime": dtime,
            "user": {"id": user},
            "event": "created",
            "sysinfo": sysinfo,
        }
    ]


def generate_meta_masterdata(config: dict) -> dict | None:
    """Populate metadata from masterdata section in config."""

    if not config:
        # this may be a temporary solution for a while, which will be told to the user
        # in related checks in dataio.py.
        warn(
            "The global config is empty, hence the 'masterdata' section "
            "in the metadata will be omitted.",
            UserWarning,
        )
        return None

    if "masterdata" not in config:
        raise ValueError("A config exists, but 'masterdata' are not present.")

    return config["masterdata"]


def generate_meta_access(config: dict) -> dict | None:
    """Populate metadata overall from access section in config + allowed keys.

    Access should be possible to change per object, based on user input.
    This is done through the access_ssdl input argument.

    The "asset" field shall come from the config. This is static information.

    The "ssdl" field can come from the config, or be explicitly given through
    the "access_ssdl" input argument. If the access_ssdl input argument is present,
    its contents shall take presedence. If no input, and no config, revert to the
    following defaults:

      access.ssdl.access_level: "internal" (we explicitly elevate to "restricted)
      access.ssdl.rep_include: False (we explicitly flag to be included in REP)

    The access.ssdl.access_level field shall be "internal" or "restricted". We still
    allow for the legacy input argument "asset", however we issue warning and change it
    to "restricted".

    The access.classification will in the future be the only information classification
    field. For now, we simply mirror it from ssdl.access_level to avoid API change.
    """

    if not config:
        warn("The config is empty or missing", UserWarning)
        return None

    if config and "access" not in config:
        raise ConfigurationError("The config misses the 'access' section")

    a_cfg = config["access"]  # shortform

    if "asset" not in a_cfg:
        # asset shall be present if config is used
        raise ConfigurationError("The 'access.asset' field not found in the config")

    # initialize and populate with defaults from config
    a_meta = {}  # shortform

    # if there is a config, the 'asset' tag shall be present
    a_meta["asset"] = a_cfg["asset"]

    # ------------------------------------
    # classification & ssdl.access_level and ssdl.rep_include
    # ------------------------------------

    # The information from the input argument "ssdl_access" has previously
    # been inserted into the config. Meaning: The fact that it sits in the config
    # at this stage, does not necessarily mean that the user actually has it in his
    # config on the FMU side. It may come from user arguments.
    # See dataio._update_globalconfig_from_settings

    # First set defaults
    a_meta["ssdl"] = {"access_level": "internal", "rep_include": False}

    # Then overwrite from config (which may also actually come from user arguments)
    if "ssdl" in a_cfg and "access_level" in a_cfg["ssdl"]:
        a_meta["ssdl"]["access_level"] = a_cfg["ssdl"]["access_level"]

    if "ssdl" in a_cfg and "rep_include" in a_cfg["ssdl"]:
        a_meta["ssdl"]["rep_include"] = a_cfg["ssdl"]["rep_include"]

    # check validity
    _valid_ssdl_access_levels = ["internal", "restricted", "asset"]
    _ssdl_access_level = a_meta["ssdl"]["access_level"]
    if _ssdl_access_level not in _valid_ssdl_access_levels:
        raise ConfigurationError(
            f"Illegal value for access.ssdl.access_level: {_ssdl_access_level} "
            f"Valid values are: {_valid_ssdl_access_levels}"
        )

    _ssdl_rep_include = a_meta["ssdl"]["rep_include"]
    if not isinstance(_ssdl_rep_include, bool):
        raise ConfigurationError(
            f"Illegal value for access.ssdl.rep_include: {_ssdl_rep_include}"
            "access.ssdl.rep_include must be a boolean (True/False)."
        )

    # if "asset", change to "restricted" and give warning
    if a_meta["ssdl"]["access_level"] == "asset":
        warn(
            "The value 'asset' for access.ssdl.access_level is deprecated. "
            "Please use 'restricted' in input arguments or global variables to silence "
            " this warning.",
            UserWarning,
        )
        a_meta["ssdl"]["access_level"] = "restricted"

    # mirror access.ssdl.access_level to access.classification
    a_meta["classification"] = a_meta["ssdl"]["access_level"]  # mirror

    return a_meta


@dataclass
class _MetaData:
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
    * meta_access: dict with name of field + access rules
    * meta_objectdata: the data block, may be complex
    * meta_display: dict of default display settings (experimental)

    """

    # input variables
    obj: Any
    dataio: Any
    compute_md5: bool = True

    # storage state variables
    objdata: Any = field(default=None, init=False)
    fmudata: Any = field(default=None, init=False)
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

        # one special case is that obj is a file path, and dataio.reuse_metadata_rule is
        # active. In this case we read the existing metadata here and reuse parts
        # according to rule described in string self.reuse_metadata_rule!
        if isinstance(self.obj, (str, Path)) and self.dataio.reuse_metadata_rule:
            logger.info("Partially reuse existing metadata from %s", self.obj)
            self.meta_existing = read_metadata(self.obj)

    def _populate_meta_objectdata(self) -> None:
        """Analyze the actual object together with input settings.

        This will provide input to the ``data`` block of the metas but has also
        valuable settings which are needed when providing filedata etc.

        Hence this must be ran early or first.
        """
        self.objdata = _ObjectDataProvider(self.obj, self.dataio, self.meta_existing)
        self.objdata.derive_metadata()
        self.meta_objectdata = self.objdata.metadata

    def _get_case_metadata(self) -> object:
        """Detect existing fmu CASE block in the metadata.

        This block may be missing in case the client is not within a FMU run, e.g.
        it runs from RMS interactive

        The _FmuDataProvider is ran first -> self.fmudata
        """
        self.fmudata = _FmuProvider(self.dataio)
        self.fmudata.detect_provider()
        logger.info("FMU provider is %s", self.fmudata.provider)
        return self.fmudata.case_metadata

    def _populate_meta_fmu(self) -> None:
        """Populate the fmu block in the metadata.

        This block may be missing in case the client is not within a FMU run, e.g.
        it runs from RMS interactive

        The _FmuDataProvider is ran first -> self.fmudata
        """
        self.fmudata = _FmuProvider(self.dataio)
        self.fmudata.detect_provider()
        logger.info("FMU provider is %s", self.fmudata.provider)
        self.meta_fmu = self.fmudata.metadata
        self.rootpath = str(self.fmudata.rootpath if self.fmudata.rootpath else "")

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

        fdata = _FileDataProvider(
            self.dataio,
            self.objdata,
            Path(self.rootpath),
            self.fmudata.iter_name,
            self.fmudata.real_name,
        )
        fdata.derive_filedata()

        self.meta_file["relative_path"] = fdata.relative_path
        self.meta_file["absolute_path"] = fdata.absolute_path
        if fdata.absolute_path_symlink:
            self.meta_file["relative_path_symlink"] = fdata.relative_path_symlink
            self.meta_file["absolute_path_symlink"] = fdata.absolute_path_symlink

        if self.compute_md5:
            if not self.objdata.extension.startswith("."):
                raise ValueError("A extension must start with '.'")
            with NamedTemporaryFile(
                buffering=0,
                suffix=self.objdata.extension,
            ) as tf:
                logger.info("Compute MD5 sum for tmp file...: %s", tf.name)
                self.meta_file["checksum_md5"] = export_file_compute_checksum_md5(
                    self.obj,
                    Path(tf.name),
                    flag=self.dataio._usefmtflag,
                )
        else:
            logger.info("Do not compute MD5 sum at this stage!")
            self.meta_file["checksum_md5"] = None

    def _populate_meta_class(self) -> None:
        """Get the general class which is a simple string."""
        self.meta_class = self.objdata.classname

    def _populate_meta_tracklog(self) -> None:
        """Create the tracklog metadata, which here assumes 'created' only."""
        self.meta_tracklog = generate_meta_tracklog()

    def _populate_meta_masterdata(self) -> None:
        """Populate metadata from masterdata section in config."""
        self.meta_masterdata = generate_meta_masterdata(self.dataio.config) or {}

    def _populate_meta_access(self) -> None:
        """Populate metadata overall from access section in config + allowed keys.

        Access should be possible to change per object, based on user input.
        This is done through the access_ssdl input argument.

        The "asset" field shall come from the config. This is static information.

        The "ssdl" field can come from the config, or be explicitly given through
        the "access_ssdl" input argument. If the access_ssdl input argument is present,
        its contents shall take presedence.

        """
        if self.dataio:
            self.meta_access = generate_meta_access(self.dataio.config) or {}

    def _populate_meta_display(self) -> None:
        """Populate the display block."""

        # display.name
        if self.dataio.display_name is not None:
            display_name = self.dataio.display_name
        else:
            display_name = self.objdata.name

        self.meta_display = {"name": display_name}

    def _populate_meta_xpreprocessed(self) -> None:
        """Populate a few necessary 'tmp' metadata needed for preprocessed data."""
        if self.dataio.fmu_context == "preprocessed":
            self.meta_xpreprocessed["name"] = self.dataio.name
            self.meta_xpreprocessed["tagname"] = self.dataio.tagname
            self.meta_xpreprocessed["subfolder"] = self.dataio.subfolder

    def _reuse_existing_metadata(self, meta: dict) -> dict:
        """Perform a merge procedure if the key `reuse_metadata_rule` is active."""
        if self.dataio and self.dataio.reuse_metadata_rule:
            oldmeta = self.meta_existing
            newmeta = meta.copy()
            if self.dataio.reuse_metadata_rule == "preprocessed":
                return glue_metadata_preprocessed(oldmeta, newmeta)
            raise ValueError(
                f"The reuse_metadata_rule {self.dataio.reuse_metadata_rule} is not "
                "supported."
            )
        return meta

    def generate_export_metadata(
        self, skip_null: bool = True
    ) -> dict:  # TODO! -> skip_null?
        """Main function to generate the full metadata"""

        # populate order matters, in particular objectdata provides input to class/file
        if self.dataio._config_is_valid:
            self._populate_meta_masterdata()
            self._populate_meta_access()

        self._populate_meta_tracklog()
        self._populate_meta_objectdata()
        self._populate_meta_class()
        self._populate_meta_fmu()
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

        if self.dataio.fmu_context == "preprocessed":
            meta["_preprocessed"] = self.meta_xpreprocessed

        if skip_null:
            meta = drop_nones(meta)

        return self._reuse_existing_metadata(meta)
