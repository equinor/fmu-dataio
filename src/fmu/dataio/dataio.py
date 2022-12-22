"""Module for DataIO class.

The metadata spec is documented as a JSON schema, stored under schema/.
"""
import logging
import os
import uuid
import warnings
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, List, Optional, Tuple, Union
from warnings import warn

import pandas as pd  # type: ignore

from . import _metadata
from ._definitions import (
    ALLOWED_CONTENTS,
    ALLOWED_FMU_CONTEXTS,
    CONTENTS_REQUIRED,
    DEPRECATED_CONTENTS,
)
from ._utils import (
    create_symlink,
    detect_inside_rms,
    drop_nones,
    export_file_compute_checksum_md5,
    export_metadata_file,
    filter_validate_metadata,
    generate_description,
    prettyprint_dict,
)
from ._utils import read_metadata as _utils_read_metadata
from ._utils import some_config_from_env, uuid_from_string

INSIDE_RMS = detect_inside_rms()


GLOBAL_ENVNAME = "FMU_GLOBAL_CONFIG"
SETTINGS_ENVNAME = "FMU_DATAIO_CONFIG"  # input settings from a spesific file!

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


class ValidationError(ValueError, KeyError):
    """Raise error while validating."""


# ======================================================================================
# Private functions
# ======================================================================================


def _validate_variable(key, value, legals) -> bool:
    """Use data from __annotions__ to validate that overriden var. is of legal type."""

    if key not in legals:
        logger.warning("Unsupported key, raise an error")
        raise ValidationError(f"The input key '{key}' is not supported")

    if isinstance(legals[key], str):
        valid_type = eval(legals[key])  # pylint: disable=eval-used
    else:
        valid_type = legals[key]

    try:
        validcheck = valid_type.__args__
    except AttributeError:
        validcheck = valid_type

    if "typing." not in str(validcheck):
        if not isinstance(value, validcheck):
            logger.warning("Wrong type of value, raise an error")
            raise ValidationError(
                f"The value of '{key}' is of wrong type: {type(value)}. "
                f"Allowed types are {validcheck}"
            )
    else:
        logger.info("Skip type checking of complex types; '%s: %s'", key, validcheck)

    return True


def _check_global_config(
    globalconfig: dict, strict: bool = True, action: str = "error"
) -> bool:
    """A minimum check/validation of the static global_config.

    Currently far from a full validation. For now, just check that some required
    keys are present in the config and warn/raise if not.
    """

    if not globalconfig and not strict:
        logger.info(
            "Empty global config, expect input from environment_variable insteac"
        )
        return False

    config_required_keys = ["access", "masterdata", "model"]
    missing_keys = []
    for required_key in config_required_keys:
        if required_key not in globalconfig:
            missing_keys.append(required_key)

    if missing_keys:
        msg = (
            "One or more keys required for valid metadata are not found: "
            f"{missing_keys} (perhaps the config is empty?) "
        )
        if "err" in action:
            msg = msg + " STOP!"
            raise ValueError(msg)
        else:
            msg += (
                "The metadata may become invalid; hence no metadata file will be made, "
                "but the data item may still be exported. Note: allowing these keys to "
                "be missing is a temporary solution that may change in future versions!"
            )
            warnings.warn(msg, PendingDeprecationWarning)

        return False

    return True


# the two next content key related function may require refactoring/simplification
def _check_content(proposed: Union[str, dict]) -> Any:
    """Check content and return a validated version."""
    logger.info("Evaluate content")

    content = proposed
    logger.debug("content is %s of type %s", str(content), type(content))
    usecontent = "unset"
    if content is None:
        warn(
            "The <content> is not provided which defaults to 'depth'. "
            "It is strongly recommended that content is given explicitly!",
            UserWarning,
        )
        usecontent = "depth"

    elif isinstance(content, str):
        logger.debug("content is a string")
        if content in CONTENTS_REQUIRED:
            raise ValidationError(f"content {content} requires additional input")
        usecontent = content
        content_specific = None  # not relevant when content is a string
        logger.debug("usecontent is %s", usecontent)

    elif isinstance(content, dict):
        logger.debug("content is a dictionary")
        usecontent = (list(content.keys()))[0]
        logger.debug("usecontent is %s", usecontent)
        content_specific = content[usecontent]
        logger.debug("content_specific is %s", content_specific)
        if not isinstance(content_specific, dict):
            raise ValueError(
                "Content is incorrectly formatted. When giving content as a dict, "
                "it must be formatted as:"
                "{'mycontent': {extra_key: extra_value} where mycontent is a string "
                "and in the list of valid contents, and extra keys in associated "
                " dictionary must be valid keys for this content."
            )
    else:
        raise ValidationError("The 'content' must be string or dict")

    if usecontent not in ALLOWED_CONTENTS.keys():
        raise ValidationError(
            f"Invalid content: <{usecontent}>! "
            f"Valid content: {', '.join(ALLOWED_CONTENTS.keys())}"
        )

    logger.debug("outgoing content is set to %s", usecontent)
    if content_specific:
        _content_validate(usecontent, content_specific)
    else:
        logger.debug("content has no extra information")

    return usecontent, content_specific


def _content_validate(name, fields):
    logger.debug("starting staticmethod _data_process_content_validate")
    valid = ALLOWED_CONTENTS.get(name, None)
    if valid is None:
        raise ValidationError(f"Cannot validate content for <{name}>")

    logger.info("name: %s", name)

    replace_deprecated = {}

    for key, dtype in fields.items():
        if key in valid.keys():
            wanted_type = valid[key]
            if not isinstance(dtype, wanted_type):
                raise ValidationError(
                    f"Invalid type for <{key}> with value <{dtype}>, not of "
                    f"type <{wanted_type}>"
                )
        elif DEPRECATED_CONTENTS.get(name, {}).get(key, None) is not None:
            logger.debug("%s/%s is deprecated, issue warning", name, key)
            replaced_by = DEPRECATED_CONTENTS[name][key].get("replaced_by", None)

            message = f"Content {name}.{key} is deprecated. "

            if replaced_by is not None:
                message += f"Please use {replaced_by}. "
                replace_deprecated.update({key: replaced_by})

            warn(
                message,
                DeprecationWarning,
            )

        else:
            raise ValidationError(f"Key <{key}> is not valid for <{name}>")

    for key, replaced_by in replace_deprecated.items():
        logger.debug("Replacing deprecated %s.%s with %s", name, key, replaced_by)
        fields[replaced_by] = fields.pop(key)
        logger.debug("Updated fields is: %s", fields)

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
    return _utils_read_metadata(filename)


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
            the file structure or by other means. See also fmu_context, where "case"
            may need an explicit casepath!

        config: Required in order to produce valid metadata, either as key (here) or
            through an environment variable. A dictionary with static settings.
            In the standard case this is read from FMU global variables
            (via fmuconfig). The dictionary must contain some
            predefined main level keys to work with fmu-dataio. If the key is missing or
            key value is None, then it will look for the environment variable
            FMU_GLOBAL_CONFIG to detect the file. If no success in finding the file, a
            UserWarning is made. If both a valid config is provided and
            FMU_GLOBAL_CONFIG is provided in addition, the latter will be used.
            Note that this key shall be set while initializing the instance, ie. it
            cannot be used in ``generate_metadata()`` or ``export()``.
            Note also: If missing or empty, export() may still be done, but without a
            metadata file (this feature may change in future releases).

        content: Optional, default is "depth". Is a string or a dictionary with one key.
            Example is "depth" or {"fluid_contact": {"xxx": "yyy", "zzz": "uuu"}}.
            Content is checked agains a white-list for validation!

        fmu_context: In normal forward models, the fmu_context is ``realization`` which
            is default and will put data per realization. Other contexts may be ``case``
            which will put data relative to the case root (see also casepath). Another
            important context is "preprocessed" which will output to a dedicated
            "preprocessed" folder instead, and metadata will be partially re-used in
            an ERT model run. If a non-FMU run is detected (e.g. you run from project),
            fmu-dataio will detect that and set actual context to None as fall-back
            (unless preprocessed is specified). If value is "preprosessed", see also
            ``resuse_metadata`` key.

        description: A multiline description of the data either as a string or a list
            of strings.

        display_name: Optional, set name for clients to use when visualizing.

        forcefolder: This setting shall only be used as exception, and will make it
            possible to output to a non-standard folder. A ``/`` in front will indicate
            an absolute path*; otherwise it will be relative to casepath or rootpath, as
            dependent on the both fmu_context and the is_observations boolean value. A
            typical use-case is forcefolder="seismic" which will replace the "cubes"
            standard folder for Cube output with "seismics". Use with care and avoid if
            possible! (*) For absolute paths, the class variable
            allow_forcefolder_absolute must set to True.

        grid_model: Currently allowed but planned for deprecation

        include_index: This applies to Pandas (table) data only, and if True then the
            index column will be exported. Deprecated, use class variable
            ``table_include_index`` instead

        is_prediction: True (default) if model prediction data

        is_observation: Default is False. If True, then disk storage will be on the
            "share/observations" folder, otherwise on share/result. An exception arise
            if fmu_context is "preprocessed", then the folder will be set to
            "share/processed" irrespective the value of is_observation.

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

        reuse_metadata_rule: This input is None or a string describing rule for reusing
            metadata. Default is None, but if the input is a file string or object with
            already valid metadata, then it is assumed to be "preprocessed", which
            merges the metadata after predefined rules.

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

        undef_is_zero: Flags that nans should be considered as zero in aggregations


    .. note:: Comment on time formats

        If two dates are present (i.e. the element represents a difference, the input
        time format is on the form::

            timedata: [[20200101, "monitor"], [20180101, "base"]]

        Hence the last data (monitor) usually comes first.

        In the new version this will shown in metadata files as where the oldest date is
        shown as t0::

            data:
              t0:
                value: 2018010T00:00:00
                description: base
              t1:
                value: 202020101T00:00:00
                description: monitor

        The output files will be on the form: somename--t1_t0.ext

    .. note:: Using config from file

        Optionally, the keys can be stored in a yaml file as argument, and you can let
        the environment variable FMU_DATAIO_CONFIG point to that file. This can e.g.
        make it possible for ERT jobs to point to external input config's. For example::

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
    allow_forcefolder_absolute: ClassVar[bool] = False
    arrow_fformat: ClassVar[str] = "arrow"
    case_folder: ClassVar[str] = "share/metadata"
    createfolder: ClassVar[bool] = True
    cube_fformat: ClassVar[str] = "segy"
    filename_timedata_reverse: ClassVar[bool] = False  # reverse order output file name
    grid_fformat: ClassVar[str] = "roff"
    include_ert2jobs: ClassVar[bool] = False  # if True, include jobs.json from ERT2
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
    description: Union[str, list] = ""
    fmu_context: str = "realization"
    forcefolder: str = ""
    grid_model: Optional[str] = None
    is_observation: bool = False
    is_prediction: bool = True
    name: str = ""
    undef_is_zero: bool = False
    parent: str = ""
    realization: int = -999
    reuse_metadata_rule: Optional[str] = None
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
    _config_is_valid: bool = field(default=True, init=False)

    # << NB! storing ACTUAL casepath:
    _rootpath: Path = field(default_factory=Path, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)
        logger.info("Running __post_init__ ExportData")
        logger.debug("Global config is %s", prettyprint_dict(self.config))

        # set defaults for mutable keys
        self.vertical_domain = {"depth": "msl"}

        # if input is provided as an ENV variable pointing to a YAML file; will override
        if SETTINGS_ENVNAME in os.environ:
            external_input = some_config_from_env(SETTINGS_ENVNAME)

            if external_input:
                # derive legal input from dataclass signature
                annots = getattr(self, "__annotations__", None)
                legals = {
                    key: val for key, val in annots.items() if not key.startswith("_")
                }

                for key, value in external_input.items():
                    if _validate_variable(key, value, legals):
                        setattr(self, key, value)
                        if key == "verbosity":
                            logger.setLevel(level=self.verbosity)

        self._config_is_valid = _check_global_config(
            self.config, strict=False, action="warn"
        )

        # global config which may be given as env variable -> a file; will override
        if GLOBAL_ENVNAME in os.environ:
            theconfig = some_config_from_env(GLOBAL_ENVNAME)
            self._config_is_valid = _check_global_config(
                theconfig, strict=True, action="warn"
            )
            if theconfig is not None:
                self.config = theconfig

        self._validate_content_key()
        logger.info("Validate FMU context which is %s", self.fmu_context)
        self._validate_fmucontext_key()
        self._update_globalconfig_from_settings()

        # check state of global config
        self._config_is_valid = _check_global_config(
            self.config, strict=True, action="warn"
        )

        self._establish_pwd_rootpath()
        self._show_deprecations_or_notimplemented()
        logger.info("FMU context is %s", self.fmu_context)
        logger.info("Ran __post_init__")

    def _show_deprecations_or_notimplemented(self):
        """Warn on deprecated keys or on stuff not implemented yet."""

        if self.runpath:
            warn(
                "The 'runpath' key has currently no function. It will be evaluated for "
                "removal in fmu-dataio version 2. Use 'casepath' instead!",
                PendingDeprecationWarning,
            )

        if self.grid_model:
            warn(
                "The 'grid_model' key has currently no function. It will be evaluated "
                "for removal in fmu-dataio version 2.",
                PendingDeprecationWarning,
            )

    def _validate_content_key(self):
        """Validate the given 'content' input."""

        self._usecontent, self._content_specific = _check_content(self.content)

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
        """Update instance settings (properties) from other routines."""
        logger.info("Try new settings %s", newsettings)

        # derive legal input from dataclass signature
        annots = getattr(self, "__annotations__", {})
        legals = {key: val for key, val in annots.items() if not key.startswith("_")}
        if "config" in legals.keys():
            del legals["config"]  # config cannot be updated

        if "config" in newsettings.keys():
            raise ValueError("Cannot have 'config' outside instance initialization")

        for setting, value in newsettings.items():
            if _validate_variable(setting, value, legals):
                setattr(self, setting, value)
                if setting == "verbosity":
                    logger.setLevel(level=self.verbosity)
                logger.info("New setting OK for %s", setting)

        self._show_deprecations_or_notimplemented()
        self._validate_content_key()
        self._validate_fmucontext_key()
        logger.info("Validate FMU context which is now %s", self.fmu_context)

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

    def _check_obj_if_file(self, obj: Any) -> Any:
        """When obj is file-like, it must be checked + assume preprocessed.

        In addition, if preprocessed, derive the subfolder if present and subfolder is
        not set already.
        """

        if isinstance(obj, (str, Path)):
            if isinstance(obj, str):
                obj = Path(obj)
            if not obj.exists():
                raise ValidationError(f"The file {obj} does not exist.")
            if not self.reuse_metadata_rule:
                self.reuse_metadata_rule = "preprocessed"

            # detect if object is on a subfolder relative to /preprocessed/xxxx
            for ipar in range(3):
                foldername = obj.parents[ipar].stem
                if foldername == "preprocessed" and ipar == 2:
                    if not self.subfolder:
                        self.subfolder = obj.parents[0].stem
                        logger.info(
                            "Subfolder is auto-derived from preprocessed file path: %s",
                            self.subfolder,
                        )
        return obj

    # ==================================================================================
    # Public methods:
    # ==================================================================================

    def generate_metadata(self, obj: Any, compute_md5: bool = True, **kwargs) -> dict:
        """Generate and return the complete metadata for a provided object.

        An object may be a map, 3D grid, cube, table, etc which is of a known and
        supported type.

        Examples of such known types are XTGeo objects (e.g. a RegularSurface),
        a Pandas Dataframe, a PyArrow table, etc.

        If the key ``reuse_metadata_rule`` is applied with legal value, the object may
        also be a reference to a file with existing metadata which then will be re-used.

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
        logger.info("KW args %s", kwargs)

        self._update_check_settings(kwargs)
        self._update_globalconfig_from_settings()

        self._config_is_valid = _check_global_config(
            self.config, strict=True, action="warn"
        )

        obj = self._check_obj_if_file(obj)
        self._establish_pwd_rootpath()
        self._validate_content_key()
        self._update_fmt_flag()

        metaobj = _metadata._MetaData(
            obj, self, compute_md5=compute_md5, verbosity=self.verbosity
        )
        self._metadata = metaobj.generate_export_metadata()

        self._rootpath = Path(metaobj.rootpath)

        logger.info("The metadata are now ready!")

        return deepcopy(self._metadata)

    def export(self, obj, return_symlink=False, **kwargs) -> str:
        """Export data objects of 'known' type to FMU storage solution with metadata.

        This function will also collect the data spesific class metadata. For "classic"
        files, the metadata will be stored i a YAML file with same name stem as the
        data, but with a . in front and "yml" and suffix, e.g.::

            top_volantis--depth.gri
            .top_volantis--depth.gri.yml

        Args:
            obj: XTGeo instance, a Pandas Dataframe instance or other supported object.
            return_symlink: If fmu_context is 'case_symlink_realization' then the link
                adress will be returned if this is True; otherwise the physical file
                path will be returned.
            **kwargs: For other arguments, see ExportData() input keys. If they
                exist both places, this function will override!

        Returns:
            String: full path to exported item.
        """
        self.generate_metadata(obj, compute_md5=False, **kwargs)
        metadata = self._metadata

        outfile = Path(metadata["file"]["absolute_path"])
        metafile = outfile.parent / ("." + str(outfile.name) + ".yml")

        useflag: Union[bool, str]
        if isinstance(obj, pd.DataFrame):
            useflag = self.table_include_index
        else:
            useflag = self._usefmtflag

        obj = self._check_obj_if_file(obj)
        logger.info("Export to file and compute MD5 sum, using flag: <%s>", useflag)
        outfile, md5 = export_file_compute_checksum_md5(
            obj, outfile, outfile.suffix, flag=useflag
        )
        # inject md5 checksum in metadata
        metadata["file"]["checksum_md5"] = md5
        logger.info("Actual file is:   %s", outfile)

        if self._config_is_valid:
            export_metadata_file(metafile, metadata, savefmt=self.meta_format)
            logger.info("Metadata file is: %s", metafile)
        else:
            warnings.warn("Metadata are invalid and will not be exported!", UserWarning)

        # generate symlink if requested
        outfile_target = None
        if metadata["file"].get("absolute_path_symlink"):
            outfile_target = Path(metadata["file"]["absolute_path_symlink"])
            outfile_source = Path(metadata["file"]["absolute_path"])
            create_symlink(outfile_source, outfile_target)
            metafile_target = outfile_target.parent / ("." + str(outfile.name) + ".yml")
            create_symlink(metafile, metafile_target)

        self._metadata = metadata

        if return_symlink and outfile_target:
            return str(outfile_target)
        else:
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
        rootfolder: To override the automatic and actual ``rootpath``. Absolute path to
            the case root, including case name. If not provided (which is not
            recommended), the rootpath will be attempted parsed from the file structure
            or by other means.
        casename: Name of case (experiment)
        caseuser: Username provided
        restart_from: ID of eventual restart
        description: Description text as string or list of strings.
        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO".
    """

    # class variables
    meta_format: ClassVar[str] = "yaml"

    # instance
    config: dict
    rootfolder: Union[str, Path, None] = None
    casename: Optional[str] = None
    caseuser: Optional[str] = None
    restart_from: Optional[str] = None
    description: Union[str, list, None] = None
    verbosity: str = "CRITICAL"

    _metadata: dict = field(default_factory=dict, init=False)
    _metafile: Path = field(default_factory=Path, init=False)
    _pwd: Path = field(default_factory=Path, init=False)
    _casepath: Path = field(default_factory=Path, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)

        if not self.config or GLOBAL_ENVNAME in os.environ:
            self.config = some_config_from_env(GLOBAL_ENVNAME)

        # For this class, the global config must be valid; hence error if not
        _check_global_config(self.config, strict=True, action="error")
        logger.info("Ran __post_init__ for InitializeCase")

    def _update_settings(self, newsettings: dict) -> None:
        """Update instance settings (properties) from other routines."""
        logger.info("Try new settings %s", newsettings)

        # derive legal input from dataclass signature
        annots = getattr(self, "__annotations__", {})
        legals = {key: val for key, val in annots.items() if not key.startswith("_")}

        for setting, value in newsettings.items():
            if _validate_variable(setting, value, legals):
                setattr(self, setting, value)
                if setting == "verbosity":
                    logger.setLevel(level=self.verbosity)
                logger.info("New setting OK for %s", setting)

    def _establish_pwd_casepath(self):
        """Establish state variables pwd and casepath.

        See ExportData's method but this is much simpler (e.g. no RMS context)
        """
        self._pwd = Path().absolute()

        if self.rootfolder:
            self._casepath = Path(self.rootfolder)
        else:
            logger.info("Emit UserWarning")
            warn(
                "The rootfolder is defaulted, but it is strongly recommended to give "
                "an explicit rootfolder",
                UserWarning,
            )
            self._casepath = self._pwd.parent.parent

        logger.info("Set PWD (case): %s", str(self._pwd))
        logger.info("Set rootpath (case): %s", str(self._casepath))

    def _check_already_metadata_or_create_folder(self, force=False) -> bool:

        if not self._casepath.exists():
            self._casepath.mkdir(parents=True, exist_ok=True)
            logger.info("Created rootpath (case) %s", self._casepath)

        metadata_path = self._casepath / "share/metadata"
        self._metafile = metadata_path / "fmu_case.yml"
        logger.info("The requested metafile is %s", self._metafile)

        if force:
            logger.info("Forcing a new metafile")

        if not self._metafile.is_file() or force:
            metadata_path.mkdir(parents=True, exist_ok=True)
            return True

        return False

    # ==================================================================================
    # Public methods:
    # ==================================================================================

    def generate_metadata(
        self, force: bool = False, skip_null=True, **kwargs
    ) -> Union[dict, None]:
        """Generate case metadata.

        Args:
            force: Overwrite existing case metadata if True. Default is False. If force
                is False and case metadata already exists, a warning will issued and
                None will be returned.
            skip_null: Fields with None/missing values will be skipped if True (default)
            **kwargs: See InitializeCase() arguments; initial will be overrided by
                settings here.

        Returns:
            A dictionary with case metadata or None
        """
        self._update_settings(kwargs)

        self._establish_pwd_casepath()
        status = self._check_already_metadata_or_create_folder(force=force)

        if status is False:
            logger.warning("The metadatafile already exists!")
            warn(
                "The metadata file already exist! Keep this file instead! "
                "To make a new case metadata file, delete the old case or use the "
                "'force' option",
                UserWarning,
            )
            return None

        meta = _metadata.default_meta_dollars()
        meta["class"] = "case"

        meta["masterdata"] = _metadata.generate_meta_masterdata(self.config)

        # only asset, not ssdl
        access = _metadata.generate_meta_access(self.config)
        meta["access"] = dict()
        meta["access"]["asset"] = access["asset"]

        meta["fmu"] = dict()
        meta["fmu"]["model"] = self.config["model"]

        mcase = meta["fmu"]["case"] = dict()
        mcase["name"] = self.casename
        mcase["uuid"] = str(uuid.uuid4())

        mcase["user"] = {"id": self.caseuser}  # type: ignore

        mcase["description"] = generate_description(self.description)  # type: ignore
        mcase["restart_from"] = self.restart_from

        meta["tracklog"] = _metadata.generate_meta_tracklog()

        if skip_null:
            meta = drop_nones(meta)

        self._metadata = meta
        logger.info("The case metadata are now ready!")
        return deepcopy(self._metadata)

    # alias
    generate_case_metadata = generate_metadata

    def export(self, force: bool = False, skip_null=True, **kwargs) -> Union[str, None]:
        """Export case metadata to file.

        Args:
            force: Overwrite existing case metadata if True. Default is False. If force
                is False and case metadata already exists, a warning will issued and
                None will be returned.
            skip_null: Fields with None/missing values will be skipped if True (default)
            **kwargs: See InitializeCase() arguments; initial will be overrided by
                settings here.

        Returns:
            Full path of metadata file or None
        """
        if self.generate_case_metadata(force=force, skip_null=skip_null, **kwargs):
            export_metadata_file(
                self._metafile, self._metadata, savefmt=self.meta_format
            )
            logger.info("METAFILE %s", self._metafile)
        else:
            warn(
                "The metadatafile exists already. use 'force' or delete the "
                "current case folder if a new metadata are requested.",
                UserWarning,
            )
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
class AggregatedData:
    """Instantate AggregatedData object.

    Args:
        aggregation_id: Give an explicit ID for the aggregation. If None, an ID will be
        made based on existing realization uuids.
        casepath: The root folder to the case, default is None. If None, the casepath
            is derived from the first input metadata paths (cf. ``source_metadata``) if
            possible. If given explicitly, the physical casepath folder must exist in
            advance, otherwise a ValueError will be raised.
        source_metadata: A list of individual metadata dictionarys, coming from the
            valid metadata per input element that forms the aggregation.
        operation: A string that describes the operation, e.g. "mean". This is
            mandatory and there is no default.
        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO".
        tagname: Additional name, as part of file name
    """

    # class variable(s)
    meta_format: ClassVar[str] = "yaml"

    # instance
    aggregation_id: Optional[str] = None
    casepath: Union[str, Path, None] = None
    source_metadata: list = field(default_factory=list)
    name: str = ""
    operation: str = ""
    tagname: str = ""
    verbosity: str = "CRITICAL"

    _metadata: dict = field(default_factory=dict, init=False)
    _metafile: Path = field(default_factory=Path, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)

    @staticmethod
    def _generate_aggr_uuid(uuids: list) -> str:
        """Unless aggregation_id; use existing UUIDs to generate a new UUID."""

        stringinput = ""
        for xuuid in sorted(uuids):
            stringinput += xuuid

        return uuid_from_string(stringinput)

    def _update_settings(self, newsettings: dict) -> None:
        """Update instance settings (properties) from other routines."""
        logger.info("Try new settings %s", newsettings)

        # derive legal input from dataclass signature
        annots = getattr(self, "__annotations__", {})
        legals = {key: val for key, val in annots.items() if not key.startswith("_")}

        for setting, value in newsettings.items():
            if _validate_variable(setting, value, legals):
                setattr(self, setting, value)
                if setting == "verbosity":
                    logger.setLevel(level=self.verbosity)
                logger.info("New setting OK for %s", setting)

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

        -----
        However, there are also the scenario that absolute_path are missing (e.g. all
        input realizations are directly made in cloud setting), and we need to
        account for that:

        infile:
           relative_path: realization-33/iter-0/share/results/maps/x.gri
           absolute_path: none

        file:
           relative_path: iter-0/share/results/maps/aggr.gri
           absolute_path: none

        -----
        Finally, a user given casepath (casepath is not None) should replace the current
        root part in the files. Like this:

        infile:
           relative_path: realization-33/iter-0/share/results/maps/x.gri
           absolute_path: /scratch/f/case/realization-33/iter-0/share/results/maps/x.gri

        casepath = /scratch/f/othercase

        result:
           relative_path: iter-0/share/results/maps/aggr.gri
           absolute_path: /scratch/f/othercase/iter-0/share/results/maps/aggrd.gri

        """
        logger.info("Construct file name for the aggregation...")
        realiname = template["fmu"]["realization"]["name"]
        relpath = template["file"]["relative_path"]

        if template["file"].get("absolute_path", None):
            abspath = template["file"]["absolute_path"]
        else:
            abspath = None

        logger.info("First input realization relpath is: %s ", relpath)
        logger.info("First input realization abspath is: %s ", abspath)

        if self.casepath:
            casepath = Path(self.casepath)
            if not casepath.exists():
                raise ValueError(
                    f"The given casepath {casepath} does not exist. "
                    "It must exist in advance!"
                )
            else:
                abspath = str(casepath / relpath)

        relpath = relpath.replace(realiname + "/", "")
        relpath = Path(relpath)
        if abspath:
            abspath = abspath.replace(realiname + "/", "")
            abspath = Path(abspath)

        suffix = relpath.suffix
        stem = relpath.stem

        usename = stem + "--" + self.operation
        if not self.name:
            warn("Input name is not given, will assume <usename>", UserWarning)
        else:
            usename = self.name

        if self.tagname:
            usename = usename + "--" + self.tagname

        relname = (relpath.parent / usename).with_suffix(suffix)

        absname = None
        if abspath:
            absname = (abspath.parent / usename).with_suffix(suffix)

        logger.info("New relpath is: %s ", relname)
        logger.info("New abspath is: %s ", absname)

        return relname, absname

    def _generate_aggrd_metadata(
        self, obj: Any, real_ids: List[int], uuids: List[str], compute_md5: bool = True
    ):

        logger.info(
            "self.aggregation is %s (%s)",
            self.aggregation_id,
            type(self.aggregation_id),
        )

        if self.aggregation_id is None:
            self.aggregation_id = self._generate_aggr_uuid(uuids)
        else:
            if not isinstance(self.aggregation_id, str):
                raise ValueError("aggregation_id must be a string")

        if not self.operation:
            raise ValueError("The 'operation' key has no value")

        # use first as template but filter away invalid entries first:
        template = filter_validate_metadata(self.source_metadata[0])

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
            "access": self.source_metadata[0]["access"],
            "masterdata": self.source_metadata[0]["masterdata"],
            "model": self.source_metadata[0]["fmu"]["model"],
        }
        etemp = ExportData(config=fakeconfig, name=self.name)
        etempmeta = etemp.generate_metadata(obj, compute_md5=compute_md5)

        template["tracklog"] = etempmeta["tracklog"]
        template["file"] = etempmeta["file"]  # actually only use the checksum_md5
        template["file"]["relative_path"] = str(relpath)
        template["file"]["absolute_path"] = str(abspath) if abspath else None

        # data section
        if self.name:
            template["data"]["name"] = self.name
        if self.tagname:
            template["data"]["tagname"] = self.tagname
        if etempmeta["data"].get("bbox"):
            template["data"]["bbox"] = etempmeta["data"]["bbox"]

        self._metadata = template

    # ==================================================================================
    # Public methods:
    # ==================================================================================

    def generate_metadata(
        self,
        obj: Any,
        compute_md5: bool = True,
        skip_null: bool = True,
        **kwargs,
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
            **kwargs: See AggregatedData() arguments; initial will be overridden by
                settings here.
        """
        logger.info("Generate metadata for class")
        self._update_settings(kwargs)

        # get input realization numbers:
        real_ids = []
        uuids = []
        for conf in self.source_metadata:
            try:
                rid = conf["fmu"]["realization"]["id"]
                xuuid = conf["fmu"]["realization"]["uuid"]
            except Exception as error:
                raise ValidationError(f"Seems that input config are not valid: {error}")

            real_ids.append(rid)
            uuids.append(xuuid)

        # first config file as template
        self._generate_aggrd_metadata(obj, real_ids, uuids, compute_md5)
        if skip_null:
            self._metadata = drop_nones(self._metadata)

        return deepcopy(self._metadata)

    # alias method
    def generate_aggregation_metadata(
        self,
        obj: Any,
        compute_md5: bool = True,
        skip_null: bool = True,
        **kwargs,
    ) -> dict:
        """Alias method name, see ``generate_metadata``"""
        return self.generate_metadata(
            obj, compute_md5=compute_md5, skip_null=skip_null, **kwargs
        )

    def export(self, obj, **kwargs) -> str:
        """Export aggregated file with metadata to file.

        Args:
            obj: Aggregated object to export, e.g. a XTGeo RegularSurface
            **kwargs: See AggregatedData() arguments; initial will be overridden by
                settings here.
        Returns:
            String: full path to exported item.
        """
        self._update_settings(kwargs)

        metadata = self.generate_metadata(obj, compute_md5=False)

        abspath = metadata["file"].get("absolute_path", None)

        if not abspath:
            raise IOError(
                "The absolute_path is None, hence no export is possible. "
                "Use the ``casepath`` key to provide a valid absolute path."
            )

        outfile = Path(abspath)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        metafile = outfile.parent / ("." + str(outfile.name) + ".yml")

        logger.info("Export to file and compute MD5 sum")
        outfile, md5 = export_file_compute_checksum_md5(obj, outfile, outfile.suffix)

        # inject the computed md5 checksum in metadata
        metadata["file"]["checksum_md5"] = md5

        export_metadata_file(metafile, metadata, savefmt=self.meta_format)
        logger.info("Actual file is:   %s", outfile)
        logger.info("Metadata file is: %s", metafile)

        self._metadata = metadata
        return str(outfile)
