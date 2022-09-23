"""Module for DataIO metadata.

This contains the _MetaData class which collects and holds all relevant metadata
"""
# https://realpython.com/python-data-classes/#basic-data-classes

import datetime
import getpass
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from warnings import warn

from fmu.dataio._definitions import SCHEMA, SOURCE, VERSION
from fmu.dataio._filedata_provider import _FileDataProvider
from fmu.dataio._fmu_provider import _FmuProvider
from fmu.dataio._objectdata_provider import _ObjectDataProvider
from fmu.dataio._utils import (
    drop_nones,
    export_file_compute_checksum_md5,
    glue_metadata_preprocessed,
    read_metadata,
)

logger = logging.getLogger(__name__)


class ConfigurationError(ValueError):
    pass


# Generic, being resused several places:


def default_meta_dollars() -> dict:
    dollars = dict()
    dollars["$schema"] = SCHEMA
    dollars["version"] = VERSION
    dollars["source"] = SOURCE
    return dollars


def generate_meta_tracklog() -> list:
    """Create the tracklog metadata, which here assumes 'created' only."""
    meta = list()

    dtime = datetime.datetime.now().isoformat()
    user = getpass.getuser()
    meta.append({"datetime": dtime, "user": {"id": user}, "event": "created"})
    return meta


def generate_meta_masterdata(config: dict) -> Optional[dict]:
    """Populate metadata from masterdata section in config."""
    if not config or "masterdata" not in config.keys():
        warn("No masterdata section present", UserWarning)
        return None

    return config["masterdata"]


def generate_meta_access(config: dict) -> Optional[dict]:
    """Populate metadata overall from access section in config + allowed keys.

    Access should be possible to change per object, based on user input.
    This is done through the access_ssdl input argument.

    The "asset" field shall come from the config. This is static information.

    The "ssdl" field can come from the config, or be explicitly given through
    the "access_ssdl" input argument. If the access_ssdl input argument is present,
    its contents shall take presedence.

    """
    if not config:
        warn("The config is empty or missing", UserWarning)
        return None

    if config and "access" not in config:
        raise ConfigurationError("The config misses the 'access' section")

    a_cfg = config["access"]

    if "asset" not in a_cfg:
        # asset shall be present if config is used
        raise ConfigurationError("The 'access.asset' field not found in the config")

    # initialize and populate with defaults from config
    a_meta = dict()  # shortform

    # if there is a config, the 'asset' tag shall be present
    a_meta["asset"] = a_cfg["asset"]

    # ssdl
    if "ssdl" in a_cfg and a_cfg["ssdl"]:
        a_meta["ssdl"] = a_cfg["ssdl"]

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
    verbosity: str = "CRITICAL"
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

    # relevant when ERT* fmu_context; same as rootpath in the ExportData class!:
    rootpath: str = field(default="", init=False)

    # if re-using existing metadata
    meta_existing: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)
        logger.info("Initialize _MetaData instance.")

        # one special case is that obj is a file path, and dataio.reuse_metadata_rule is
        # active. In this case we read the existing metadata here and reuse parts
        # according to rule described in string self.reuse_metadata_rule!
        if isinstance(self.obj, (str, Path)) and self.dataio.reuse_metadata_rule:
            logger.info("Partially reuse existing metadata from %s", self.obj)
            self.meta_existing = read_metadata(self.obj)

    def _populate_meta_objectdata(self):
        """Analyze the actual object together with input settings.

        This will provide input to the ``data`` block of the metas but has also
        valuable settings which are needed when providing filedata etc.

        Hence this must be ran early or first.
        """
        self.objdata = _ObjectDataProvider(self.obj, self.dataio, self.meta_existing)
        self.objdata.derive_metadata()
        self.meta_objectdata = self.objdata.metadata

    def _get_case_metadata(self):
        """Detect existing fmu CASE block in the metadata.

        This block may be missing in case the client is not within a FMU run, e.g.
        it runs from RMS interactive

        The _FmuDataProvider is ran first -> self.fmudata
        """
        self.fmudata = _FmuProvider(self.dataio, verbosity=self.verbosity)
        self.fmudata.detect_provider()
        logger.info("FMU provider is %s", self.fmudata.provider)
        return self.fmudata.case_metadata

    def _populate_meta_fmu(self):
        """Populate the fmu block in the metadata.

        This block may be missing in case the client is not within a FMU run, e.g.
        it runs from RMS interactive

        The _FmuDataProvider is ran first -> self.fmudata
        """
        self.fmudata = _FmuProvider(self.dataio, verbosity=self.verbosity)
        self.fmudata.detect_provider()
        logger.info("FMU provider is %s", self.fmudata.provider)
        self.meta_fmu = self.fmudata.metadata
        self.rootpath = self.fmudata.rootpath

    def _populate_meta_file(self):
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
            self.rootpath,
            self.fmudata.iter_name,
            self.fmudata.real_name,
            self.verbosity,
        )
        fdata.derive_filedata()

        self.meta_file["relative_path"] = fdata.relative_path
        self.meta_file["absolute_path"] = fdata.absolute_path
        if fdata.absolute_path_symlink:
            self.meta_file["relative_path_symlink"] = fdata.relative_path_symlink
            self.meta_file["absolute_path_symlink"] = fdata.absolute_path_symlink

        if self.compute_md5:
            logger.info("Compute MD5 sum for tmp file...")
            _, self.meta_file["checksum_md5"] = export_file_compute_checksum_md5(
                self.obj,
                "tmp",
                self.objdata.extension,
                tmp=True,
                flag=self.dataio._usefmtflag,
            )
        else:
            logger.info("Do not compute MD5 sum at this stage!")
            self.meta_file["checksum_md5"] = None

    def _populate_meta_class(self):
        """Get the general class which is a simple string."""
        self.meta_class = self.objdata.classname

    def _populate_meta_tracklog(self):
        """Create the tracklog metadata, which here assumes 'created' only."""
        self.meta_tracklog = generate_meta_tracklog()

    def _populate_meta_masterdata(self):
        """Populate metadata from masterdata section in config."""
        self.meta_masterdata = generate_meta_masterdata(self.dataio.config)

    def _populate_meta_access(self):
        """Populate metadata overall from access section in config + allowed keys.

        Access should be possible to change per object, based on user input.
        This is done through the access_ssdl input argument.

        The "asset" field shall come from the config. This is static information.

        The "ssdl" field can come from the config, or be explicitly given through
        the "access_ssdl" input argument. If the access_ssdl input argument is present,
        its contents shall take presedence.

        """
        if self.dataio:
            self.meta_access = generate_meta_access(self.dataio.config)

    def _reuse_existing_metadata(self, meta):
        """Perform a merge procedure if the key `reuse_metadata_rule` is active."""
        if self.dataio and self.dataio.reuse_metadata_rule:
            oldmeta = self.meta_existing
            newmeta = meta.copy()
            if self.dataio.reuse_metadata_rule == "preprocessed":
                return glue_metadata_preprocessed(oldmeta, newmeta)
            else:
                raise ValueError(
                    f"The reuse_metadata_rule {self.dataio.reuse_metadata_rule} is not "
                    "supported."
                )
        return meta

    def generate_export_metadata(self, skip_null=True) -> dict:  # TODO! -> skip_null?
        """Main function to generate the full metadata"""

        # populate order matters, in particular objectdata provides input to class/file
        self._populate_meta_masterdata()
        self._populate_meta_tracklog()
        self._populate_meta_access()
        self._populate_meta_objectdata()
        self._populate_meta_class()
        self._populate_meta_fmu()
        self._populate_meta_file()

        # glue together metadata, order is as legacy code (but will be screwed if reuse
        # of existing metadata...)
        meta = self.meta_dollars.copy()
        meta["tracklog"] = self.meta_tracklog
        meta["class"] = self.meta_class

        meta["fmu"] = self.meta_fmu
        meta["file"] = self.meta_file

        meta["data"] = self.meta_objectdata
        meta["display"] = {"name": self.dataio.name}  # solution so far; TBD

        meta["access"] = self.meta_access
        meta["masterdata"] = self.meta_masterdata

        if skip_null:
            meta = drop_nones(meta)

        meta = self._reuse_existing_metadata(meta)

        return meta
