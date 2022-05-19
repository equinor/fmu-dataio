"""Module for DataIO class.

The metadata spec is documented as a JSON schema, stored under schema/.
"""
import logging
import os
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, List, Optional, Tuple, Union
from warnings import warn

import pandas as pd
import yaml

from ._definitions import ALLOWED_CONTENTS, ALLOWED_FMU_CONTEXTS, CONTENTS_REQUIRED
from ._metadata import _MetaData
from ._utils import (
    detect_inside_rms,
    drop_nones,
    export_file_compute_checksum_md5,
    export_metadata_file,
    prettyprint_dict,
    some_config_from_env,
    uuid_from_string,
)

INSIDE_RMS = detect_inside_rms()

# class variables
CLASSVARS = [
    "arrow_fformat",
    "case_folder",
    "createfolder",
    "cube_fformat",
    "grid_fformat",
    "legacy_time_format",
    "meta_format",
    "points_fformat",
    "polygons_fformat",
    "surface_fformat",
    "table_fformat",
    "table_include_index",
    "verifyfolder",
    "_inside_rms",  # pretend inside RMS! developer only
]

# possible user inputs:
INSTANCEVARS = {
    "access_ssdl": dict,
    "casepath": (str, Path, None),
    "config": dict,
    "content": (dict, str),
    "depth_reference": str,
    "description": str,
    "fmu_context": str,
    "forcefolder": (str, Path),
    "is_observation": bool,
    "is_prediction": bool,
    "name": str,
    "parent": str,
    "realization": int,
    "runpath": str,
    "tagname": str,
    "timedata": list,
    "subfolder": str,
    "unit": str,
    "verbosity": str,
    "vertical_domain": dict,
    "workflow": str,
}

GLOBAL_ENVNAME = "FMU_GLOBAL_CONFIG"
SETTINGS_ENVNAME = "FMU_DATAIO_CONFIG"  # input settings from a file!

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


class ValidationError(ValueError):
    """Raise error while validating."""


# ======================================================================================
# Private functions
# ======================================================================================


def _check_global_config(globalconfig: dict, strict: bool = True):
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


# the two next content key related function may require refactoring/simplification
def _check_content(proposed: Union[str, dict]) -> Any:
    """Check content and return a validated version."""
    logger.info("Evaluate content")

    content = proposed
    logger.debug("content is %s of type %s", str(content), type(content))
    usecontent = "unset"
    useextra = None
    if content is None:
        warn(
            "The <content> is not provided which defaults to 'depth'. "
            "It is strongly recommended that content is given explicitly!",
            UserWarning,
        )
        usecontent = "depth"

    elif isinstance(content, str):
        if content in CONTENTS_REQUIRED:
            raise ValidationError(f"content {content} requires additional input")
        usecontent = content

    elif isinstance(content, dict):
        usecontent = (list(content.keys()))[0]
        useextra = content[usecontent]

    else:
        raise ValidationError("The 'content' must be string or dict")

    if usecontent not in ALLOWED_CONTENTS.keys():
        raise ValidationError(
            f"Invalid content: <{usecontent}>! "
            f"Valid content: {', '.join(ALLOWED_CONTENTS.keys())}"
        )

    logger.debug("outgoing content is set to %s", usecontent)
    if useextra:
        _content_validate(usecontent, useextra)
        return {usecontent: useextra}
    else:
        logger.debug("content has no extra information")
        return usecontent


def _content_validate(name, fields):
    logger.debug("starting staticmethod _data_process_content_validate")
    valid = ALLOWED_CONTENTS.get(name, None)
    if valid is None:
        raise ValidationError(f"Cannot validate content for <{name}>")

    logger.info("name: %s", name)

    for key, dtype in fields.items():
        if key in valid.keys():
            wanted_type = valid[key]
            if not isinstance(dtype, wanted_type):
                raise ValidationError(
                    f"Invalid type for <{key}> with value <{dtype}>, not of "
                    f"type <{wanted_type}>"
                )
        else:
            raise ValidationError(f"Key <{key}> is not valid for <{name}>")

    required = CONTENTS_REQUIRED.get(name, None)
    if isinstance(required, dict):
        rlist = list(required.items())
        logger.info("rlist is %s", rlist)
        logger.info("fields is %s", fields)
        rkey, status = rlist.pop()
        logger.info("rkey not in fields.keys(): %s", str(rkey not in fields.keys()))
        logger.info("rkey: %s", rkey)
        logger.info("fields.keys(): %s", str(fields.keys()))
        if rkey not in fields.keys() and status is True:
            raise ValidationError(
                f"The subkey <{rkey}> is required for content <{name}> ",
                "but is not found",
            )


# ======================================================================================
# Public function to read/load assosiated metadata given a file (e.g. a map file)
# ======================================================================================


def read_metadata(filename: Union[str, Path]) -> dict:
    """Read the metadata as a dictionary given a filename.

    If the filename is e.g. /some/path/mymap.gri, the assosiated metafile
    will be /some/path/.mymap.gri.yml (or json?)

    Args:
        filename: The full path filename to the data-object.

    Returns:
        A dictionary with metadata read from the assiated metadata file.
    """
    fname = Path(filename)
    metafile = str(fname.parent) + "/." + fname.stem + fname.suffix + ".yml"
    metafilepath = Path(metafile)
    if not metafilepath.exists():
        raise IOError(f"Cannot find requested metafile: {metafile}")
    with open(metafilepath, "r") as stream:
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
            poly = xtgeo.polygons_from_roxar(PRJ, hname, POL_FOLDER)

            out = ed.export(poly, name=name)

    Almost all keyword settings like ``name``, ``tagname`` etc can be set in both the
    ExportData instance and directly in the ``generate_metadata`` or ``export()``
    function, to provide flexibility for different use cases. If both are set, the
    ``export()`` setting will win followed by ``generate_metadata() and finally
    ExportData()``.

    A note on 'pwd' and 'rootpath' and 'casepath': The 'pwd' is the process working
    directory, which is folder where the process (script) starts. The 'rootpath' is the
    folder from which relative file names are relative to and is normally auto-detected.
    The user can however force set the 'actual' rootpath by providing the input
    `casepath`. In case of running a RMS project interactive on disk::

        /project/foo/resmod/ff/2022.1.0/rms/model                   << pwd
        /project/foo/resmod/ff/2022.1.0/                            << rootpath

        A file:

        /project/foo/resmod/ff/2022.1.0/share/results/maps/xx.gri   << example absolute
                                        share/results/maps/xx.gri   << example relative

    When running an ERT2 forward job using a normal ERT job (e.g. a script)::

        /scratch/nn/case/realization-44/iter-2                      << pwd
        /scratch/nn/case                                            << rootpath

        A file:

        /scratch/nn/case/realization-44/iter-2/share/results/maps/xx.gri  << absolute
                         realization-44/iter-2/share/results/maps/xx.gri  << relative

    When running an ERT2 forward job but here executed from RMS::

        /scratch/nn/case/realization-44/iter-2/rms/model            << pwd
        /scratch/nn/case                                            << rootpath

        A file:

        /scratch/nn/case/realization-44/iter-2/share/results/maps/xx.gri  << absolute
                         realization-44/iter-2/share/results/maps/xx.gri  << relative


    Args:

        access_ssdl: Optional. A dictionary that will overwrite or append
             to the default ssdl settings read from the config. Example:
            ``{"access_level": "restricted", "rep_include": False}``

        casepath: To override the automatic and actual ``rootpath``. Absolute path to
            the case root. If not provided, the rootpath will be attempted parsed from
            the file structure or by other means. Use with care!

        config: Required, either as key (here) or through an environment variable.
            A dictionary with static settings. In the standard case this is read
            from FMU global variables (via fmuconfig). The dictionary must contain some
            predefined main level keys to work with fmu-dataio. If the key is missing or
            key value is None, then it will look for the environment variable
            FMU_GLOBAL_CONFIG to detect the file. If no success in finding the file, a
            UserWarning is made. If both a valid config is provided and
            FMU_GLOBAL_CONFIG is provided in addition, the latter will be used.

        content: Optional, default is "depth". Is a string or a dictionary with one key.
            Example is "depth" or {"fluid_contact": {"xxx": "yyy", "zzz": "uuu"}}.
            Content is checked agains a white-list for validation!

        fmu_context: In normal forward models, the fmu_context is ``realization`` which
            is default and will put data per realization. Other contexts may be ``case``
            which willput data relative to the case root. If a non-FMU run is detected
            (e.g. you run from project), fmu-dataio will detect that and set actual
            context to None as fall-back.

        description: A multiline description of the data.

        display_name: Optional, set name for clients to use when visualizing.

        forcefolder: This setting shall only be used as exception, and will make it
            possible to output to a non-standard folder. A ``/`` in front will indicate
            an absolute path; otherwise it will be relative to casepath/rootpath.
            Use with care.

        include_index: This applies to Pandas (table) data only, and if True then the
            index column will be exported. Deprecated, use class variable
            ``table_include_index`` instead

        is_prediction: True (default) if model prediction data

        is_observation: Default is False. If True, then disk storage will be on the
            "share/observations" folder, otherwise on share/result

        name: Optional but recommended. The name of the object. If not set it is tried
            to be inferred from the xtgeo/pandas/... object. The name is then checked
            towards the stratigraphy list, and name is replaced with official
            stratigraphic name if found in static metadata `stratigraphy`. For example,
            if "TopValysar" is the model name and the actual name is "Valysar Top Fm."
            that latter name will be used.

        parent: Optional. This key is required for datatype GridProperty, and
            refers to the name of the grid geometry.

        realization: Optional, default is -999 which means that realization shall be
            detected automatically from the FMU run. Can be used to override in rare
            cases. If so, numbers must be >= 0

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
            [[20200101, "monitor"], [20180101, "base"]] or just [[2021010]]. The output
            to metadata will from version 0.9 be different (API change)

        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO", "DEBUG". Default is
            "CRITICAL".

        vertical_domain: This is dictionary with a key and a reference e.g.
            {"depth": "msl"} which is default if missing.

        workflow: Short tag desciption of workflow (as description)


    .. note:: Comment on time formats

        If two dates are present (i.e. the element represents a difference, the input
        time format is on the form::

            timedata: [[20200101, "monitor"], [20180101, "base"]]

        Hence the last data (monitor) usually comes first.

        In the new version this will shown in metadata files as where the oldest date is
        shown as t0::

            data:
              t0:
                value: 2018010T00:00:00 description: base
              t1:
                value: 202020101T00:00:00 description: monitor

        The output files will be on the form: somename--t1_t0.ext

    .. note:: Using config from file

        Optionally, the keys can be stored in a yaml file as argument, and you can let
        the environment variable FMU_DATAIO_CONFIG point to that file. This can e.g.
        make it possible for ERT jobs to point to external input configs. For example::

            export FMU_DATAIO_CONFIG="/path/to/mysettings.yml"
            export FMU_GLOBAL_CONFIG="/path/to/global_variables.yml"

        In python:

            eda = ExportData()
            eda.export(obj)


    """

    # ----------------------------------------------------------------------------------
    # This role for this class is to be:
    # - public (end user) interface
    # - collect the full settings from global config, user keys and class variables
    # - process and validate these settings
    # - establish PWD and rootpath
    #
    # Then other classes will further do the detailed metadata processing, cf _MetaData
    # and subsequent classes called by _MetaData
    # ----------------------------------------------------------------------------------

    # class variables
    arrow_fformat: ClassVar[str] = "arrow"
    case_folder: ClassVar[str] = "share/metadata"
    createfolder: ClassVar[bool] = True
    cube_fformat: ClassVar[str] = "segy"
    grid_fformat: ClassVar[str] = "roff"
    legacy_time_format: ClassVar[bool] = False
    meta_format: ClassVar[str] = "yaml"
    polygons_fformat: ClassVar[str] = "csv"  # or use "csv|xtgeo"
    points_fformat: ClassVar[str] = "csv"  # or use "csv|xtgeo"
    surface_fformat: ClassVar[str] = "irap_binary"
    table_fformat: ClassVar[str] = "csv"
    table_include_index: ClassVar[bool] = False
    verifyfolder: ClassVar[bool] = True
    _inside_rms: ClassVar[bool] = False  # developer only! if True pretend inside RMS

    # input keys (alphabetic)
    access_ssdl: dict = field(default_factory=dict)
    aggregation: bool = False
    casepath: Union[str, Path, None] = None
    config: dict = field(default_factory=dict)
    content: Union[dict, str] = "depth"
    depth_reference: str = "msl"
    description: str = ""
    fmu_context: str = "realization"
    forcefolder: str = ""
    is_observation: bool = False
    is_prediction: bool = True
    name: str = ""
    parent: str = ""
    realization: int = -999
    runpath: Union[str, Path, None] = None
    subfolder: str = ""
    tagname: str = ""
    timedata: Optional[List[list]] = None
    unit: str = ""
    verbosity: str = "CRITICAL"
    vertical_domain: dict = field(default_factory=dict)
    workflow: str = ""

    # some keys that are modified version of input, prepended with _use
    _usecontent: dict = field(default_factory=dict, init=False)
    _usecontext: str = field(default="", init=False)
    _usefmtflag: str = field(default="", init=False)

    # storing resulting state variables for instance, non-public:
    _metadata: dict = field(default_factory=dict, init=False)
    _pwd: Path = field(default_factory=Path, init=False)

    # << NB! storing ACTUAL casepath:
    _rootpath: Path = field(default_factory=Path, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)
        logger.info("Running __post_init__ ...")
        logger.debug("Global config is %s", prettyprint_dict(self.config))

        # set defaults for mutable keys
        self.vertical_domain = {"depth": "msl"}

        _check_global_config(self.config, strict=False)

        # if input is provided as an ENV variable pointing to a YAML file; will override
        if SETTINGS_ENVNAME in os.environ:
            external_config = some_config_from_env(SETTINGS_ENVNAME)
            for key, value in external_config.items():
                if key not in INSTANCEVARS:
                    raise ValidationError(f"Proposed setting {key} is not valid")

                if isinstance(value, (str, float, int)):
                    logger.info("Setting external key and value: %s: %s", key, value)
                else:
                    logger.info(
                        "Setting external key and value: %s: %s", key, "dict/list..."
                    )

                setattr(self, key, value)

        # global config which may be given as env variable -> a file; will override
        if not self.config or GLOBAL_ENVNAME in os.environ:
            self.config = some_config_from_env(GLOBAL_ENVNAME)

        self._validate_content_key()
        self._validate_fmucontext_key()
        self._update_globalconfig_from_settings()
        _check_global_config(self.config, strict=True)
        self._establish_pwd_rootpath()

        self._show_deprecations_or_notimplemented()
        logger.info("Ran __post_init__")

    def _show_deprecations_or_notimplemented(self):
        """Warn on deprecated keys og on stuff not implemented yet."""

        if self.runpath:
            warn(
                "The 'runpath' key has currently no function. It will be evaluated for "
                "removal in fmu-dataio version 1. Use 'casepath' instead!",
                PendingDeprecationWarning,
            )

    def _validate_content_key(self):
        """Validate the given 'content' input."""

        updated_content = _check_content(self.content)
        # keep the updated content as extra setting
        self._usecontent = updated_content

    def _validate_fmucontext_key(self):
        """Validate the given 'fmu_context' input."""
        if self.fmu_context not in ALLOWED_FMU_CONTEXTS:
            msg = ""
            for key, value in ALLOWED_FMU_CONTEXTS.items():
                msg += f"{key}: {value}\n"
            raise ValidationError(
                "It seems like 'fmu_context' value is illegal! "
                f"Allowed entries are: in list:\n{msg}"
            )

    def _update_fmt_flag(self) -> None:
        # treat special handling of "xtgeo" in format name:
        if self.points_fformat == "csv|xtgeo" or self.polygons_fformat == "csv|xtgeo":
            self._usefmtflag = "xtgeo"
        logger.info("Using flag format: <%s>", self._usefmtflag)

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
                setattr(self, setting, value)

        self._show_deprecations_or_notimplemented()
        self._validate_content_key()
        self._validate_fmucontext_key()

    def _update_globalconfig_from_settings(self):
        """A few user settings may update/append the global config directly."""
        newglobals = deepcopy(self.config)

        if self.access_ssdl:
            if "ssdl" not in self.config["access"]:
                newglobals["access"]["ssdl"] = dict()

            newglobals["access"]["ssdl"] = deepcopy(self.access_ssdl)

            logger.info(
                "Updated global config's access.ssdl value: %s", newglobals["access"]
            )

        self.config = newglobals

    def _establish_pwd_rootpath(self):
        """Establish state variables pwd and the (initial) rootpath.

        The self._pwd stores the process working directory, i.e. the folder
        from which the process is ran

        The self._rootpath stores the folder from which is the base root for all
        relative output files. This rootpath may be dependent on if this is a FMU run
        or just an interactive run.

        Hence this 'initial' rootpath can be updated later!
        """
        logger.info(
            "Establish pwd and actual casepath, inside RMS flag is %s (actual: %s))",
            self._inside_rms,
            INSIDE_RMS,
        )
        self._pwd = Path().absolute()

        # fmu_context 1: Running RMS, we are in conventionally in rootpath/rms/model
        # fmu_context 2: ERT FORWARD_JOB, at case = rootpath=RUNPATH/../../. level
        # fmu_context 3: ERT WORKFLOW_JOB, running somewhere/anywhere else

        self._rootpath = self._pwd
        if self.casepath and isinstance(self.casepath, (str, Path)):
            self._rootpath = Path(self.casepath).absolute()
            logger.info("The casepath is hard set as %s", self._rootpath)

        else:
            if self._inside_rms or INSIDE_RMS or "RUN_DATAIO_EXAMPLES" in os.environ:

                self._rootpath = (self._pwd / "../../.").absolute().resolve()
                logger.info("Run from inside RMS (or pretend)")
                self._inside_rms = True
        # make some extra keys in settings:
        self._usecontext = self.fmu_context  # may change later!

        logger.info("pwd:        %s", str(self._pwd))
        logger.info("rootpath:   %s", str(self._rootpath))

    # ==================================================================================
    # Public methods:
    # ==================================================================================

    def generate_metadata(self, obj: Any, compute_md5: bool = True, **kwargs) -> dict:
        """Generate and return the complete metadata for a provided object.

        An object may be a map, 3D grid, cube, table, etc which is of a known and
        supported type.

        Examples of such known types are XTGeo objects (e.g. a RegularSurface),
        a Pandas Dataframe, a PyArrow table, etc.

        Args:
            obj: XTGeo instance, a Pandas Dataframe instance or other supported object.
            compute_md5: If True, compute a MD5 checksum for the exported file.
            **kwargs: For other arguments, see ExportData() input keys. If they
                exist both places, this function will override!

        Returns:
            A dictionary with all metadata.

        Note:
            If the ``compute_md5`` key is False, the ``file.checksum_md5`` will be
            empty. If true, the MD5 checksum will be generated based on export to
            a temporary file, which may be time-consuming if the file is large.
        """
        logger.info("Generate metadata...")

        self._update_check_settings(kwargs)
        self._update_globalconfig_from_settings()
        _check_global_config(self.config)
        self._establish_pwd_rootpath()
        self._validate_content_key()
        self._update_fmt_flag()

        metaobj = _MetaData(
            obj, self, compute_md5=compute_md5, verbosity=self.verbosity
        )
        self._metadata = metaobj.generate_export_metadata()

        self._rootpath = metaobj.rootpath

        logger.info("The metadata are now ready!")

        return deepcopy(self._metadata)

    def export(self, obj, **kwargs) -> str:
        """Export data objects of 'known' type to FMU storage solution with metadata.

        This function will also collect the data spesific class metadata. For "classic"
        files, the metadata will be stored i a YAML file with same name stem as the
        data, but with a . in front and "yml" and suffix, e.g.::

            top_volantis--depth.gri
            .top_volantis--depth.gri.yml

        Args:
            obj: XTGeo instance, a Pandas Dataframe instance or other supported object.
            **kwargs: For other arguments, see ExportData() input keys. If they
                exist both places, this function will override!

        Returns:
            String: full path to exported item.
        """

        self.generate_metadata(obj, compute_md5=False, **kwargs)
        metadata = self._metadata

        outfile = Path(metadata["file"]["absolute_path"])
        metafile = outfile.parent / ("." + str(outfile.name) + ".yml")

        if isinstance(obj, pd.DataFrame):
            useflag = self.table_include_index
        else:
            useflag = self._usefmtflag

        logger.info("Export to file and compute MD5 sum, using flag: <%s>", useflag)
        outfile, md5 = export_file_compute_checksum_md5(
            obj, outfile, outfile.suffix, flag=useflag
        )

        # inject md5 checksum in metadata
        metadata["file"]["checksum_md5"] = md5

        export_metadata_file(metafile, metadata)
        logger.info("Actual file is:   %s", outfile)
        logger.info("Metadata file is: %s", metafile)

        self._metadata = metadata

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

        casepath: To override the automatic and actual ``rootpath``. Absolute path to
            the case root. If not provided, the rootpath will be attempted parsed from
            the file structure or by other means.

        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO".
    """

    config: dict
    casepath: Union[str, Path, None] = None
    verbosity: str = "CRITICAL"

    _metadata: dict = field(default_factory=dict, init=False)
    _metafile: Path = field(default_factory=Path, init=False)
    _pwd: Path = field(default_factory=Path, init=False)
    _rootpath: Path = field(default_factory=Path, init=False)

    def __post_init__(self):

        logger.setLevel(level=self.verbosity)

        if not self.config or GLOBAL_ENVNAME in os.environ:
            self.config = some_config_from_env(GLOBAL_ENVNAME)

        _check_global_config(self.config)
        self._edata = ExportData(config=self.config)  # dummy

    def _establish_pwd_rootpath(self):
        """Establish state variables pwd and casepath.

        See ExportData's method but this is much simpler (e.g. no RMS context)
        """
        self._pwd = Path().absolute()

        if self.casepath:
            self._rootpath = self.casepath
        else:
            self._rootpath = self._pwd.parent.parent

        logger.info("Set PWD (case): %s", str(self._pwd))
        logger.info("Set rootpath (case): %s", str(self._rootpath))

    def _get_case_metadata(self) -> dict:
        """Get the current case medata"""
        self._establish_pwd_rootpath()

        metaobj = _MetaData(
            None, self._edata, initialize_case=True, verbosity=self.verbosity
        )
        return metaobj._get_case_metadata()

    def generate_case_metadata(self, force: bool = False) -> dict:
        self._establish_pwd_rootpath()

        metaobj = _MetaData(
            None, self._edata, initialize_case=True, verbosity=self.verbosity
        )

        self._metadata = metaobj.generate_case_metadata(force=force)
        self._metafile = metaobj.fmudata.case_metafile

        logger.info("The case metadata are now ready!")
        return deepcopy(self._metadata)

    def export(self, force=False) -> str:
        """Export case metadata to file.

        Returns:
            String: full path to exported metadata file.
        """

        self.generate_case_metadata(force=force)
        export_metadata_file(self._metafile, self._metadata)
        logger.info("METAFILE %s", self._metafile)
        return str(self._metafile)


# ######################################################################################
# AggregatedData
#
# The AggregatedData is used for making the aggregations from existing data that already
# have valid metadata, i.e. made from ExportData.
#
# Hence this is actually quite different and simpler than ExportData(), which
# needed a lot of info as FmuProvider, FileProvider, ObjectData etc. Here most these
# already known from the input.
#
# For aggregations, the id is normally given as an argument by the external process, and
# by that, be able to give a group of aggregations the same id.
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
        tagname: Additional name, as part of file name
        aggregation_id: Give an explicit ID for the aggregation. If set to True, an
            automatic ID based on existing realization uuid will be made.
            Default is None which means it will be missing (null) in the metadata.
    """

    configs: list = field(default_factory=list)
    operation: str = "unknown"
    name: str = ""
    tagname: str = ""
    aggregation_id: Optional[Union[str, bool]] = None
    verbosity: str = "CRITICAL"

    _metadata: dict = field(default_factory=dict, init=False)
    _metafile: Path = field(default_factory=Path, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)

    @staticmethod
    def _generate_aggr_uuid(uuids: list) -> str:
        """Unless aggregation_id; use existing UUIDs to generate a new UUID."""

        stringinput = ""
        for uuid in uuids:
            stringinput += uuid

        return uuid_from_string(stringinput)

    def _construct_filename(self, template: dict) -> Tuple[Path, Path]:
        """Construct the paths/filenames for aggregated data.

        These filenames are constructed a bit different than in a forward job, since we
        do not now which folder we 'are in' when doing aggregations. Could possibly also
        be in a cloud setting.

        Hence we use the first input realization as template, e.g.:

        file:
           relative_path: realization-33/iter-0/share/results/maps/x.gri
           absolute_path: /scratch/f/case/realization-33/iter-0/share/results/maps/x.gri

        And from thet we derive/compose the relative and absolute path for the
        aggregated data:

        file:
           relative_path: iter-0/share/results/maps/aggr.gri
           absolute_path: /scratch/f/case/iter-0/share/results/maps/aggr.gri

        The trick is to replace 'realization-*' with nothing and create a new file
        name.
        """
        logger.info("Construct file name for the aggregation...")
        realiname = template["fmu"]["realization"]["name"]
        relpath = template["file"]["relative_path"]
        abspath = template["file"]["absolute_path"]

        logger.info("First input realization relpath is: %s ", relpath)
        logger.info("First input realization abspath is: %s ", abspath)

        relpath = relpath.replace(realiname + "/", "")
        abspath = abspath.replace(realiname + "/", "")

        relpath = Path(relpath)
        abspath = Path(abspath)
        suffix = abspath.suffix
        stem = abspath.stem

        usename = stem + "--" + self.operation
        if not self.name:
            warn("Input name is not given, will assume <usename>", UserWarning)
        else:
            usename = self.name

        if self.tagname:
            usename = usename + "--" + self.tagname

        relname = (relpath.parent / usename).with_suffix(suffix)
        absname = (abspath.parent / usename).with_suffix(suffix)

        logger.info("New relpath is: %s ", relname)
        logger.info("New abspath is: %s ", absname)

        return relname, absname

    def _generate_aggrd_metadata(
        self, obj: Any, real_ids: List[int], uuids: List[str], compute_md5: bool = True
    ):

        if self.aggregation_id is None:
            self.aggregation_id = None
        elif self.aggregation_id is True:
            self.aggregation_id = self._generate_aggr_uuid(uuids)

        template = deepcopy(self.configs[0])

        relpath, abspath = self._construct_filename(template)

        # fmu.realization shall not be used
        del template["fmu"]["realization"]

        template["fmu"]["aggregation"] = dict()
        template["fmu"]["aggregation"]["operation"] = self.operation
        template["fmu"]["aggregation"]["realization_ids"] = real_ids
        template["fmu"]["aggregation"]["id"] = self.aggregation_id

        # next, the new object will trigger update of: 'file', 'data' (some fields) and
        # 'tracklog'. The trick is to create an ExportData() instance and just retrieve
        # the metadata from that, and then blend the needed metadata from here into the
        # template -> final metadata

        fakeconfig = {
            "access": self.configs[0]["access"],
            "masterdata": self.configs[0]["masterdata"],
            "model": self.configs[0]["fmu"]["model"],
        }
        etemp = ExportData(config=fakeconfig)
        etempmeta = etemp.generate_metadata(obj, compute_md5=compute_md5)

        template["tracklog"] = etempmeta["tracklog"]
        template["file"] = etempmeta["file"]  # actually only use the checksum_md5
        template["file"]["relative_path"] = relpath
        template["file"]["absolute_path"] = abspath

        # data section
        if self.name:
            template["data"]["name"] = self.name
        if self.tagname:
            template["data"]["tagname"] = self.tagname

        template["data"]["bbox"] = etempmeta["data"]["bbox"]

        self._metadata = template

    def generate_aggregation_metadata(
        self,
        obj: Any,
        compute_md5: bool = True,
        skip_null: bool = True,
    ) -> dict:
        """Generate metadata for the aggregated data.

        This is a quite different and much simpler operation than the ExportData()
        version, as here most metadata for each input element are already known. Hence,
        the metadata for the first element in the input list is used as template.

        Args:

            obj: The map, 3D grid, table, etc instance.

            compute_md5: If True, an md5 sum for the file will be created. This involves
                a temporary export of the data, and may be time consuming for large
                data.

            skip_null: If True (default), None values in putput will be skipped
        """
        logger.info("Generate metadata for class")

        # get input realization numbers:
        real_ids = []
        uuids = []
        for conf in self.configs:
            try:
                rid = conf["fmu"]["realization"]["id"]
                uuid = conf["fmu"]["realization"]["uuid"]
            except Exception as error:
                raise ValidationError(f"Seems that input config are not valid: {error}")

            real_ids.append(rid)
            uuids.append(uuid)

        # first config file as template
        self._generate_aggrd_metadata(obj, real_ids, uuids, compute_md5)
        if skip_null:
            self._metadata = drop_nones(self._metadata)

        return deepcopy(self._metadata)

    def export(self, obj) -> str:
        """Export aggregated file with metadata to file.

        Returns:
            String: full path to exported item.
        """
        metadata = self.generate_aggregation_metadata(obj, compute_md5=False)

        outfile = Path(metadata["file"]["absolute_path"])
        metafile = outfile.parent / ("." + str(outfile.name) + ".yml")

        logger.info("Export to file and compute MD5 sum")
        outfile, md5 = export_file_compute_checksum_md5(obj, outfile, outfile.suffix)

        # inject the computed md5 checksum in metadata
        metadata["file"]["checksum_md5"] = md5

        export_metadata_file(metafile, metadata)
        logger.info("Actual file is:   %s", outfile)
        logger.info("Metadata file is: %s", metafile)

        self._metadata = metadata
        return str(outfile)
