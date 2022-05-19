"""Module for DataIO metadata.

This contains the _MetaData class which collects and holds all relevant metadata
"""
# https://realpython.com/python-data-classes/#basic-data-classes

import datetime
import getpass
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any
from warnings import warn

from fmu.dataio._definitions import SCHEMA, SOURCE, VERSION
from fmu.dataio._filedata_provider import _FileDataProvider
from fmu.dataio._fmu_provider import _FmuProvider
from fmu.dataio._objectdata_provider import _ObjectDataProvider
from fmu.dataio._utils import drop_nones, export_file_compute_checksum_md5

logger = logging.getLogger(__name__)


def default_meta_dollars():
    dollars = dict()
    dollars["$schema"] = SCHEMA
    dollars["version"] = VERSION
    dollars["source"] = SOURCE
    return dollars


class ConfigurationError(ValueError):
    pass


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
    initialize_case: bool = False
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

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)
        logger.info("Initialize _MetaData instance.")

    def _populate_meta_objectdata(self):
        """Analyze the actual object together with input settings.

        This will provide input to the ``data`` block of the metas but has also
        valuable settings which are needed when providing filedata etc.

        Hence this must be ran early or first.
        """
        if self.initialize_case:
            return

        self.objdata = _ObjectDataProvider(self.obj, self.dataio)
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
        meta = list()

        dtime = datetime.datetime.now().isoformat()
        user = getpass.getuser()
        meta.append({"datetime": dtime, "user": {"id": user}, "event": "created"})
        self.meta_tracklog = meta

    def _populate_meta_masterdata(self):
        """Populate metadata from masterdata section in config.

        Having the `masterdata` as hardcoded first level in the config is intentional.
        If that section is missing, or config is None, return with a user warning.
        """
        if not self.dataio.config or "masterdata" not in self.dataio.config.keys():
            warn("No masterdata section present", UserWarning)
            self.meta_masterdata = None
            return

        self.meta_masterdata = self.dataio.config["masterdata"]

        # TODO! validation

    def _populate_meta_access(self):
        """Populate metadata overall from access section in config + allowed keys.

        Access should be possible to change per object, based on user input.
        This is done through the access_ssdl input argument.

        The "asset" field shall come from the config. This is static information.

        The "ssdl" field can come from the config, or be explicitly given through
        the "access_ssdl" input argument. If the access_ssdl input argument is present,
        its contents shall take presedence.

        """
        if not self.dataio.config:
            warn("The config is empty or missing", UserWarning)
            return

        if self.dataio.config and "access" not in self.dataio.config:
            raise ConfigurationError("The config misses the 'access' section")

        a_cfg = self.dataio.config["access"]

        if "asset" not in a_cfg:
            # asset shall be present if config is used
            raise ConfigurationError("The 'access.asset' field not found in the config")

        # initialize and populate with defaults from config
        a_meta = self.meta_access = dict()  # shortform

        # if there is a config, the 'asset' tag shall be present
        a_meta["asset"] = a_cfg["asset"]

        # ssdl
        if "ssdl" in a_cfg and a_cfg["ssdl"]:
            a_meta["ssdl"] = a_cfg["ssdl"]

        # if isinstance(access_ssdl, dict):
        #     a_meta["ssdl"] = access_ssdl

        # TODO! validate

        # TODO!?  case??
        # # if input argument, expand or overwrite ssdl tag contents from config
        # if not self._case and self._access_ssdl is not None:
        #     a_meta["ssdl"] = {**a_meta["ssdl"], **self._access_ssdl}

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

        # glue together metadata, order is as legacy code
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

        return meta

    def generate_case_metadata(
        self, skip_null=True, force=False, restart_from=None, description=None
    ) -> dict:
        """Main function to generate the metadata for case, cf InitializeCase"""

        logger.info("Generate case metadata")
        self._populate_meta_masterdata()
        self._populate_meta_fmu()
        self._populate_meta_access()

        if self.fmudata.case_metadata and not force:
            raise ValueError(
                "Case metadata already exists. Use force=True to re-generate"
            )
        meta = self.meta_dollars.copy()
        meta["class"] = "case"

        meta["masterdata"] = self.meta_masterdata

        # only asset, not ssdl
        meta["access"] = dict()
        meta["access"]["asset"] = self.meta_access["asset"]

        meta["fmu"] = dict()
        meta["fmu"]["model"] = self.dataio.config["model"]

        mcase = meta["fmu"]["case"] = dict()
        mcase["name"] = self.fmudata.case_name
        mcase["uuid"] = str(uuid.uuid4())

        mcase["user"] = {"id": self.fmudata.user_name}

        mcase["description"] = description
        mcase["restart_from"] = restart_from

        if skip_null:
            meta = drop_nones(meta)

        return meta
