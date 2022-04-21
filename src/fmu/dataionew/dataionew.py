"""Module for DataIO class.

The metadata spec is documented as a JSON schema, stored under schema/.
"""
import logging
import os
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, List, Union
from warnings import warn

import yaml

import fmu.dataionew._utils as utils
from fmu.dataionew._definitions import ALLOWED_CONTENTS
from fmu.dataionew._metadata import _MetaData
from fmu.dataionew._utils import C, G, S

CLASSVARS = [
    "arrow_fformat",
    "case_folder",
    "createfolder",
    "cube_fformat",
    "grid_fformat",
    "meta_format",
    "points_fformat",
    "polygons_fformat",
    "surface_fformat",
    "table_fformat",
    "verifyfolder",
    "_inside_rms",
]

INSTANCEVARS = {
    "access_ssdl": dict,
    "casepath": (str, Path, None),
    "config": dict,
    "content": (dict, str),
    "context": (dict, str),
    "forcefolder": (str, Path),
    "is_observation": bool,
    "is_prediction": bool,
    "name": str,
    "parentname": str,
    "realization": int,
    "tagname": str,
    "time1": (int, str, datetime),
    "time2": (int, str, datetime),
    "subfolder": str,
    "unit": str,
    "verbosity": str,
    "vertical_domain": dict,
    "workflow": str,
}

XTGEO_EXPORTS = ("surface", "polygons")
PANDAS_EXPORTS = "tables"
GLOBAL_ENVNAME = "FMU_GLOBAL_CONFIG"

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


class ValidationError(ValueError):
    """Raise error while validating."""

    ...


def _check_global_config(globalconfig, strict=True):
    """A check/validation of static global_config.

    Currently not a full validation. For now, just check that some required
    keys are present in the config and raise if not.
    """

    if not globalconfig and not strict:
        warn(
            "Empty global config, expect input from environment_variable instead",
            UserWarning,
        )
        return

    config_required_keys = ["access", "masterdata", "model"]
    for required_key in config_required_keys:
        if required_key not in globalconfig:
            raise ValidationError(f"Required key '{required_key}' not found in config.")


# ======================================================================================
# Public function to read/load assosiated metadata given a file
# ======================================================================================


def read_metadata(filename: Union[str, Path]) -> dict:
    """Read the metadata as a dictionary given a filename.

    If the filename is e.g. /some/path/mymap.gri, the assosiated metafile
    will be /some/path/.mymap.gri.yml (or json?)

    Args:
        filename: The full path filename to the data-object.

    Returns:
        A dictionary with metadata.
    """
    fname = Path(filename)
    metafile = str(fname.parent) + "/." + fname.stem + fname.suffix + ".yml"
    metafile = Path(metafile)
    if not metafile.exists():
        raise IOError(f"Cannot find requested metafile: {metafile}")
    with open(metafile, "r") as stream:
        metacfg = yaml.safe_load(stream)

    return metacfg


# ======================================================================================
# ExportData, public class
# ======================================================================================


@dataclass
class ExportData:
    """Class for exporting data with rich metadata in FMU.

    This class sets up the general metadata content to be applied in export. The idea is
    that one ExportData instance can be re-used for several similar export() jobs. For
    example::

        edata = dataio.ExportData(
            config=CFG, content="depth", unit="m", vertical_domain={"depth": "msl"},
            timedata=None, is_prediction=True, is_observation=False,
            tagname="faultlines", workflow="rms structural model",
        )

        for name in ["TopOne", TopTwo", "TopThree"]:
            poly = xtgeo.polygons_from_roxar(PRJ, hname, POL_FOLDER) out =
            ed.export(poly, name=name)

    Almost all keyword settings like ``name``, ``tagname`` etc can be set in both the
    ExportData instance and directly in the ``generate_metadata`` or ``export()``
    function, to provide flexibility for different use cases. If both are set, the
    ``export()`` setting will win followed by ``generate_metadata() and finally
    ExportData()``.


    Args:

        access_ssdl: Optional. A dictionary that will overwrite or append
             to the default ssdl settings read from the config. Example:
            ``{"access_level": "restricted", "rep_include": False}``

        aggregation: Optional bool, default is False. If the input is known to be an
            aggregation (e.g. mean of many surfaces), set to True.

        casepath: Absolute path to the case root. If not provided, it will be attempted
            parsed from the file structure. This setting is current inactive and
            deprecated

        config: Required, a configuation dictionary. In the standard case this is read
            from FMU global variables (via fmuconfig). The dictionary must contain some
            predefined main level keys to work with fmu-dataio. If the key is missing or
            key value is None, then it will look for the environment variable
            FMU_GLOBAL_CONFIG to detect the file. If no success in finding the file, a
            UserWarning is made. If both a valid config is provided and
            FMU_GLOBAL_CONFIG is provided in addition, the latter will be used.

        content: Optional, default is "depth". Is a string or a dictionary with one key.
            Example is "depth" or {"fluid_contact": {"xxx": "yyy", "zzz": "uuu"}}.
            Content is checked agains a white-list for validation!

        context: Deprecated? TODO?

        description: A multiline description of the data.

        display_name: Optional, set name for clients to use when visualizing.

        forcefolder: This setting shall only be used as exception, and will make it
            possible to output to a non-standard folder. A ``/`` in front will indicate
            an absolute path; otherwise it will be relative to CASEPATH. Use with care.

        include_index: This applies to Pandas (table) data only, and if True then the
            index column will be exported.

        is_prediction: True (default) if model prediction data

        is_observation: Default is False. If True, then disk storage will be on the
            "share/observations" folder, otherwise on share/result

        name: Optional but recommended. The name of the object. If not set it is tried
            to be inferred from the xtgeo/pandas/... object. The name is then checked
            towards the stratigraphy list, and name is replaced with official
            stratigraphic name if found in static metadata `stratigraphy`. For example,
            if "TopValysar" is the model name and the actual name is "Valysar Top Fm."
            that latter name will be used.

        parentname: Optional. This key is required for datatype GridProperty, and refers to
            the name of the grid geometry.

        realization: Optional, default is -999 which means that realization shall be
            detected automatically from the FMU run. Can be used to override in
            rare cases. If so, numbers must be >= 0

        runpath: TODO! Optional and deprecated. The relative location of the current run
            root. Optional and will in most cases be auto-detected, assuming that FMU
            folder conventions are followed. For an ERT run e.g.
            /scratch/xx/nn/case/realization-0/iter-0/. while in a revision at project
            disc it will the revision root e.g. /project/xx/resmod/ff/21.1.0/.

        subfolder: It is possible to set one level of subfolders for file output.
            The input should only accept a single folder name, i.e. no paths. If paths
            are present, a deprecation warning will be raised.

        tagname: This is a short tag description which be be a part of file name.

        timedata: If given, a list of lists with dates, .e.g.
            [[20200101, "monitor"], [20180101, "base"]] or just [[2021010]].
            TODO! Consider deprecate this input variant?

        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO", "DEBUG". Default is
            "CRITICAL".

        vertical_domain: This is dictionary with a key and a reference e.g.
            {"depth": "msl"} which is default if missing.

        workflow: Short tag desciption of workflow (as description)
    """

    # ----------------------------------------------------------------------------------
    # This role for this class is to be
    # - public (end user) interface
    # - collect the full settings from global config, user keys and class variables
    # - process and validate these settings
    # - establish PWD and BASEPATH
    #
    # Then other classes will further do the detailed metadata processing, cf _MetaData
    # and subsequent classes called by _MetaData
    # ----------------------------------------------------------------------------------

    # class variables
    surface_fformat: ClassVar[str] = "irap_binary"
    table_fformat: ClassVar[str] = "csv"
    arrow_fformat: ClassVar[str] = "arrow"
    polygons_fformat: ClassVar[str] = "csv"  # or use "csv|xtgeo"
    points_fformat: ClassVar[str] = "csv"  # or use "csv|xtgeo"
    grid_fformat: ClassVar[str] = "roff"
    cube_fformat: ClassVar[str] = "segy"
    case_folder: ClassVar[str] = "share/metadata"
    createfolder: ClassVar[bool] = True
    verifyfolder: ClassVar[bool] = True
    meta_format: ClassVar[str] = "yaml"
    _inside_rms: ClassVar[bool] = False  # developer only! if True pretend inside RMS

    # input keys (alphabetic)
    access_ssdl: dict = field(default_factory=dict)
    aggregation: bool = False
    casepath: Union[str, Path, None] = None
    config: dict = field(default_factory=dict)
    content: Union[dict, str] = "depth"
    context: Union[dict, str] = ""
    forcefolder: str = ""
    is_observation: bool = False
    is_prediction: bool = True
    name: str = ""
    parentname: str = ""  # TODO: parent?
    realization: int = -999
    subfolder: str = ""
    tagname: str = ""
    time1: str = ""
    time2: str = ""
    unit: str = ""
    verbosity: str = "CRITICAL"
    vertical_domain: dict = field(default_factory=dict)
    workflow: str = ""

    # storing resulting state variables for instance:
    metadata: dict = field(default_factory=dict, init=False)
    cfg: dict = field(default_factory=dict, init=False)
    pwd: Path = field(default_factory=Path, init=False)
    basepath: Path = field(default_factory=Path, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)
        logger.info("Running __post_init__ ...")
        logger.debug("Global config is %s", utils.prettyprint_dict(self.config))

        # set defaults for mutable keys
        self.vertical_domain = {"depth": "msl"}

        if self.aggregation:
            raise NotImplementedError("Aggregation not yet implemented")

        _check_global_config(self.config, strict=False)

        # collect all given settings in master dictionary: self.cfg
        self.cfg[C] = dict()  # the class variables
        self.cfg[G] = dict()  # global config variables
        self.cfg[S] = dict()  # the other settings

        # store Class variables
        for cvar in CLASSVARS:
            self.cfg[C][cvar] = getattr(self, cvar)

        # store input key values except config (which are the static global_config)
        for ivar in INSTANCEVARS:
            if "config" in ivar:
                self.cfg[G] = getattr(self, ivar)
            else:
                self.cfg[S][ivar] = getattr(self, ivar)

        # special; global config which may be given as env variable pointing on a file
        if not self.cfg[G] or GLOBAL_ENVNAME in os.environ:
            self.cfg[G] = utils.global_config_from_env(GLOBAL_ENVNAME)

        logger.info("Input access: %s", self.cfg[G]["access"])

        self._validate_content_key()
        self._update_globalconfig_from_settings()
        _check_global_config(self.cfg[G], strict=True)
        self._establish_pwd_basepath()

        self._show_deprecations()
        logger.info("Ran __post_init__")

    def _show_deprecations(self):
        """Warn on deprecated keys."""

        if self.cfg[S]["casepath"] is not None:
            warn(
                "The 'casepath' key is deprecated and has no function. It may be "
                "removed in fmu-dataio version 1",
                DeprecationWarning,
            )

        # not sure what to do with 'context'
        if self.cfg[S]["context"]:
            warn(
                "The 'context' key has currently no function. It will be evaluated for "
                "removal in fmu-dataio version 1",
                PendingDeprecationWarning,
            )

    def _validate_content_key(self):
        """Validate the given 'content' input."""
        if self.cfg[S]["content"] not in ALLOWED_CONTENTS:
            msg = ""
            for key, value in ALLOWED_CONTENTS.items():
                msg += f"{key}: {value}\n"
            raise ValidationError(
                "It seems like 'content' value is illegal! "
                f"Allowed entries are: in list:\n{msg}"
            )
        # TODO! CONTENT_REQUIRED

    def _update_check_settings(self, newsettings: dict) -> None:
        """If settings "S" are updated, run a validation prior update self._settings."""

        logger.info("New settings %s", newsettings)
        for setting, value in newsettings.items():
            if setting not in INSTANCEVARS:
                raise ValidationError(f"Proposed setting {setting} is not valid")
            else:
                logger.info("Value type %s", type(value))
                if not isinstance(value, INSTANCEVARS[setting]):
                    raise ValidationError("Setting key is present but incorrect type")
                self.cfg[S][setting] = value
        self._show_deprecations()

    def _update_globalconfig_from_settings(self):
        """A few user settings may update/append the global config directly."""
        newglobals = deepcopy(self.cfg[G])

        if "access_ssdl" in self.cfg[S] and self.cfg[S]["access_ssdl"]:
            if "ssdl" not in self.cfg[G]["access"]:
                newglobals["access"]["ssdl"] = dict()

            newglobals["access"]["ssdl"] = deepcopy(self.cfg[S]["access_ssdl"])
            del self.cfg[S]["access_ssdl"]

            logger.info(
                "Updated global config's access.ssdl value: %s", newglobals["access"]
            )

        self.cfg[G] = newglobals

    def _establish_pwd_basepath(self):
        """Establish state variables pwd and basepath.

        The self.pwd stores the process working directory, i.e. the folder
        from which the process is ran

        The self.basepath stores the folder from which is the base root for all
        relative output files.
        """
        logger.info("Establish pwd and basepath, inside RMS is %s)", self._inside_rms)
        self.pwd = Path().absolute()

        # Context 1: Running RMS, we are in conventionally in basepath/rms/model
        # Context 2: ERT FORWARD_JOB, running at basepath=RUNPATH level
        # Context 3: ERT WORKFLOW_JOB, running somewhere/anywhere else

        self.basepath = self.pwd
        if self.basepath and isinstance(self.basepath, (str, Path)):
            self.basepath = Path(self.basepath).absolute()
            logger.info("The basepath is hard set as %s", self.basepath)

        if self._inside_rms or (
            "rms" in sys.executable and "komodo" not in sys.executable
        ):
            self.basepath = (self.pwd / "../../.").absolute().resolve()
            logger.info("Run from inside RMS (or pretend)")

        if "RUN_DATAIO_EXAMPLES" in os.environ:  # special; for repo doc examples!
            self.basepath = Path("../../.").absolute().resolve()

        self.cfg[S]["pwd"] = self.pwd
        self.cfg[S]["basepath"] = self.basepath

        logger.info("pwd:      %s", str(self.pwd))
        logger.info("basepath: %s", str(self.basepath))

    # ==================================================================================
    # Public methods:
    # ==================================================================================

    def generate_metadata(self, obj: Any, compute_md5: bool = True, **kwargs) -> dict:
        """Generate the complete (except MD5 sum) metadata for a provided object.

        An object may be a map, 3D grid, cube, table, etc which is of a known and
        supported type.

        Examples of such known types are XTGeo objects (e.g. a RegularSurface),
        a Pandas Dataframe, etc.

        This function will also collect the data spesific class metadata. For "classic"
        files, the metadata will be stored i a YAML file with same name stem as the
        data, but with a . in front and "yml" and suffix, e.g.::

            top_volantis--depth.gri
            .top_volantis--depth.gri.yml

        For formats supporting embedded metadata, other solutions may be used.

        Args:
            obj: XTGeo instance, a Pandas Dataframe instance or other supported object.
            compute_md5: If True, compute a MD5 checksum for the exported file.
            **kwargs: For other arguments, see ExportData() input keys. If they
                exist both places, the latter will override!
        """
        self._update_check_settings(kwargs)
        self._update_globalconfig_from_settings()
        _check_global_config(self.config)
        self._establish_pwd_basepath()
        self._validate_content_key()

        metaobj = _MetaData(
            obj, self.cfg, compute_md5=compute_md5, verbosity=self.verbosity
        )
        self.metadata = metaobj.generate_metadata()
        logger.info("The metadata are now ready!")

        return deepcopy(self.metadata)

    def export(self, obj, **kwargs) -> str:
        """Export data objects of 'known' type to FMU storage solution with metadata.

        Args:
            See arguments for ``generate_metadata``

        Returns:
            String: full path to exported item.
        """

        metadata = self.generate_metadata(obj, compute_md5=False, **kwargs)

        outfile = Path(metadata["file"]["absolute_path"])
        metafile = outfile.parent / ("." + str(outfile.name) + ".yml")

        logger.info("Export to file and compute MD5 sum")
        outfile, md5 = utils.export_file_compute_checksum_md5(
            obj, outfile, outfile.suffix
        )

        # inject md5 checksum in metadata
        metadata["file"]["checksum_md5"] = md5

        utils.export_metadata_file(metafile, metadata)
        logger.info("Actual file is:   %s", outfile)
        logger.info("Metadata file is: %s", metafile)

        self.metadata = metadata

        return str(outfile)


# ######################################################################################
# InitializeCase.
#
# The InitializeCase is used for making the case matadata prior to any other actions,
# e.g. forward jobs. However, case metadata file may already exist, and in that case
# this class should only emit a message or warning
# ######################################################################################


@dataclass
class InitializeCase:  # pylint: disable=too-few-public-methods
    """Instantate InitializeCase object.

    In ERT this is typically ran as an hook workflow in advance.

    Args:
        config: A configuration dictionary. In the standard case this is read
            from FMU global variables (via fmuconfig). The dictionary must contain
            some predefined main level keys. If config is None or the env variable
            FMU_GLOBAL_CONFIG pointing to a file is provided, then it will attempt to
            parse that file instead.
        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO".
    """

    config: dict
    verbosity: str = "CRITICAL"

    cfg: dict = field(default_factory=dict, init=False)
    metadata: dict = field(default_factory=dict, init=False)
    metafile: Path = field(default_factory=Path, init=False)
    pwd: Path = field(default_factory=Path, init=False)
    basepath: Path = field(default_factory=Path, init=False)

    def __post_init__(self):

        logger.setLevel(level=self.verbosity)

        if not self.config or GLOBAL_ENVNAME in os.environ:
            self.config = utils.global_config_from_env(GLOBAL_ENVNAME)

        _check_global_config(self.config)

        # collect all given settings in dictionary self.cfg since _Metadata expects that
        self.cfg[C] = dict()  # the class variables (may be empty here)
        self.cfg[G] = self.config  # global config variables
        self.cfg[S] = dict()  # the other settings (may be empty here)

    def _establish_pwd_basepath(self):
        """Establish state variables pwd and basepath.

        See ExportData's method but this is much simpler (e.g. no RMS context)
        """
        self.pwd = Path().absolute()

        self.basepath = self.pwd
        self.cfg[S]["pwd"] = self.pwd
        self.cfg[S]["basepath"] = self.basepath

        logger.info("Set PWD (case): %s", str(self.pwd))
        logger.info("Set BASEPATH (case): %s", str(self.basepath))

    def _get_case_metadata(self) -> dict:
        """Get the current case medata"""
        self._establish_pwd_basepath()

        metaobj = _MetaData(
            None, self.cfg, initialize_case=True, verbosity=self.verbosity
        )
        return metaobj._get_case_metadata()

    def generate_case_metadata(self, force: bool = False) -> dict:
        self._establish_pwd_basepath()

        metaobj = _MetaData(
            None, self.cfg, initialize_case=True, verbosity=self.verbosity
        )

        self.metadata = metaobj.generate_case_metadata(force=force)
        self.metafile = metaobj.fmudata.case_metafile

        logger.info("The case metadata are now ready!")
        return deepcopy(self.metadata)

    def export(self, force=False) -> str:
        """Export case metadata to file.

        Returns:
            String: full path to exported item.
        """

        self.generate_case_metadata(force=force)
        utils.export_metadata_file(self.metafile, self.metadata)
        logger.info("METAFILE %s", self.metafile)
        return str(self.metafile)


# ######################################################################################
# AggregatedData
#
# The AggregatedData is used for making the aggregations from existing data that already
# have valid metadata, i.e. made from ExportData.
#
# Hence this is actually quite different and much simpler than ExportData(), which
# needed a lot of info as FmuProvider, FileProvider, ObjectData etc. Here all these
# already known from the input.
#
# ######################################################################################


@dataclass
class AggregatedData:  # pylint: disable=too-few-public-methods
    """Instantate AggregatedData object.

    Args:
        configs: A list of dictionarys, i.e. of valid metadata per input element
        operation: A string that descibes the operation, e.g. "mean"
        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO".
    """

    configs: list = field(default_factory=list)
    operation: str = "unknown"
    verbosity: str = "CRITICAL"

    metadata: dict = field(default_factory=dict, init=False)
    metafile: Path = field(default_factory=Path, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)

    @staticmethod
    def _generate_aggr_uuid(uuids: list) -> str:
        """Use existing UUIDs to generate a new UUID for the aggregation."""

        stringinput = ""
        for uuid in uuids:
            stringinput += uuid

        return utils.uuid_from_string(stringinput)

    def _generate_aggrd_metadata(self, obj: Any, real_ids: List[int], uuids: List[str]):

        agg_uuid = self._generate_aggr_uuid(uuids)

        template = deepcopy(self.configs[0])

        del template["fmu"]["iteration"]
        del template["fmu"]["realization"]

        template["fmu"]["aggregation"] = dict()
        template["fmu"]["aggregation"]["operation"] = self.operation
        template["fmu"]["aggregation"]["realization_ids"] = real_ids
        template["fmu"]["aggregation"]["id"] = agg_uuid

        # next, the new object will trigger update of:
        # 'file', 'data' (some fields) and 'tracklog'. The trick is to create an
        # ExportData() instance and just retrieve the metadata from that, and then
        # blend the needed metadata from here into the template
        fakeconfig = {
            "access": self.configs[0]["access"],
            "masterdata": self.configs[0]["masterdata"],
            "model": self.configs[0]["fmu"]["model"],
        }
        etemp = ExportData(config=fakeconfig)
        etempmeta = etemp.generate_metadata(obj, compute_md5=True)

        template["tracklog"] = etempmeta["tracklog"]
        template["file"] = etempmeta["file"]
        template["data"]["bbox"] = etempmeta["data"]["bbox"]

        self.metadata = template

    def generate_metadata(self, obj: Any) -> dict:
        """Generate metadata for the aggregated data.

        This is a quite different and much simpler operation than the ExportData()
        version, as here most metadata for each input element are already known.
        """
        logger.info("Generate metadata for %s", __class__)

        # get input realization numbers:
        real_ids = []
        uuids = []
        for conf in self.configs:
            try:
                rid = conf["fmu"]["realization"]["id"]
                uuid = conf["fmu"]["realization"]["uuid"]
            except Exception as error:
                raise ValidationError(f"Seems that input config are not valid: {error}")
            finally:
                real_ids.append(rid)
                uuids.append(uuid)

        # first config file as template
        self._generate_aggrd_metadata(obj, real_ids, uuids)

        return deepcopy(self.metadata)

    def export(self) -> str:
        """Export case metadata to file.

        Returns:
            String: full path to exported item.
        """

        print("Not yet there!")
