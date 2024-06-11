"""Module for DataIO class.

The metadata spec is documented as a JSON schema, stored under schema/.
"""

from __future__ import annotations

import os
import warnings
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, Final, List, Literal, Optional, Union
from warnings import warn

from . import types
from ._definitions import (
    FmuContext,
    ValidationError,
)
from ._logging import null_logger
from ._metadata import generate_export_metadata
from ._utils import (
    detect_inside_rms,  # dataio_examples,
    export_file,
    export_metadata_file,
    prettyprint_dict,
    read_metadata_from_file,
    some_config_from_env,
)
from .aggregation import AggregatedData
from .case import InitializeCase
from .datastructure.configuration import global_configuration
from .datastructure.meta import enums
from .preprocessed import ExportPreprocessedData
from .providers._fmu import FmuProvider, get_fmu_context_from_environment

# DATAIO_EXAMPLES: Final = dataio_examples()
INSIDE_RMS: Final = detect_inside_rms()


GLOBAL_ENVNAME: Final = "FMU_GLOBAL_CONFIG"
SETTINGS_ENVNAME: Final = (
    "FMU_DATAIO_CONFIG"  # Feature deprecated, still used for user warning.
)

logger: Final = null_logger(__name__)

AggregatedData: Final = AggregatedData  # Backwards compatibility alias
InitializeCase: Final = InitializeCase  # Backwards compatibility alias


# ======================================================================================
# Private functions
# ======================================================================================


def _future_warning_preprocessed() -> None:
    warnings.warn(
        "Using the ExportData class for re-exporting preprocessed data is no "
        "longer supported. Use the dedicated ExportPreprocessedData class "
        "instead. In a deprecation period the ExportPreprocessedData is used "
        "under the hood when a filepath is input to ExportData. "
        "Please update your script, as this will be discontinued in the future.",
        FutureWarning,
    )


def _validate_variable(key: str, value: type, legals: dict[str, str | type]) -> bool:
    """Use data from __annotions__ to validate that overriden var. is of legal type."""
    if key not in legals:
        logger.warning("Unsupported key, raise an error")
        raise ValidationError(f"The input key '{key}' is not supported")

    legal_key = legals[key]
    # Potential issue: Eval will use the modules namespace. If given
    #   "from typing import ClassVar" or similar.
    # is missing from the namespace, eval(...) will fail.
    valid_type = eval(legal_key) if isinstance(legal_key, str) else legal_key

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


# ======================================================================================
# Public function to read/load assosiated metadata given a file (e.g. a map file)
# ======================================================================================


def read_metadata(filename: str | Path) -> dict:
    """Read the metadata as a dictionary given a filename.

    If the filename is e.g. /some/path/mymap.gri, the assosiated metafile
    will be /some/path/.mymap.gri.yml (or json?)

    Args:
        filename: The full path filename to the data-object.

    Returns:
        A dictionary with metadata read from the assiated metadata file.
    """
    return read_metadata_from_file(filename)


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

    When running an ERT forward job using a normal ERT job (e.g. a script)::

        /scratch/nn/case/realization-44/iter-2                      << pwd
        /scratch/nn/case                                            << rootpath

        A file:

        /scratch/nn/case/realization-44/iter-2/share/results/maps/xx.gri  << absolute
                         realization-44/iter-2/share/results/maps/xx.gri  << relative

    When running an ERT forward job but here executed from RMS::

        /scratch/nn/case/realization-44/iter-2/rms/model            << pwd
        /scratch/nn/case                                            << rootpath

        A file:

        /scratch/nn/case/realization-44/iter-2/share/results/maps/xx.gri  << absolute
                         realization-44/iter-2/share/results/maps/xx.gri  << relative


    Args:
        access_ssdl: Optional. A dictionary that will overwrite or append
            to the default ssdl settings read from the config. Example:
            ``{"access_level": "restricted", "rep_include": False}``
            Deprecated and replaced by 'classification' and 'rep_include' arguments.

        casepath: To override the automatic and actual ``rootpath``. Absolute path to
            the case root. If not provided, the rootpath will be attempted parsed from
            the file structure or by other means. See also fmu_context, where "case"
            may need an explicit casepath!

        classification: Optional. Security classification level of the data object.
            If present it will override the default found in the config.
            Valid values are either "restricted" or "internal".

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
            (unless preprocessed is specified). If this key is not explicitly given it
            will be inferred to be either "case"/"realization"/"non-fmu" based on the
            presence of ERT environment variables.

        description: A multiline description of the data either as a string or a list
            of strings.

        display_name: Optional, set name for clients to use when visualizing.

        forcefolder: This setting shall only be used as exception, and will make it
            possible to output to a non-standard folder relative to casepath/rootpath,
            as dependent on the both fmu_context and the is_observations boolean value.
            A typical use-case is forcefolder="seismic" which will replace the "cubes"
            standard folder for Cube output with "seismics". Use with care and avoid if
            possible!

        grid_model: Currently allowed but planned for deprecation

        table_index: This applies to Pandas (table) data only, and is a list of the
            column names to use as index columns e.g. ["ZONE", "REGION"].

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

        rep_include: Optional. If True then the data object will be available in REP.
            Default is False.

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
    allow_forcefolder_absolute: ClassVar[bool] = False  # deprecated
    arrow_fformat: ClassVar[str] = "parquet"
    case_folder: ClassVar[str] = "share/metadata"
    createfolder: ClassVar[bool] = True  # deprecated
    cube_fformat: ClassVar[str] = "segy"
    filename_timedata_reverse: ClassVar[bool] = False  # reverse order output file name
    grid_fformat: ClassVar[str] = "roff"
    include_ertjobs: ClassVar[bool] = False  # deprecated
    legacy_time_format: ClassVar[bool] = False  # deprecated
    meta_format: ClassVar[Literal["yaml", "json"]] = "yaml"
    polygons_fformat: ClassVar[str] = "csv"  # or use "csv|xtgeo"
    points_fformat: ClassVar[str] = "csv"  # or use "csv|xtgeo"
    surface_fformat: ClassVar[str] = "irap_binary"
    table_fformat: ClassVar[str] = "csv"
    dict_fformat: ClassVar[str] = "json"
    table_include_index: ClassVar[bool] = False  # deprecated
    verifyfolder: ClassVar[bool] = True  # deprecated
    _inside_rms: ClassVar[bool] = False  # developer only! if True pretend inside RMS

    # input keys (alphabetic)
    access_ssdl: dict = field(default_factory=dict)
    aggregation: bool = False
    casepath: Optional[Union[str, Path]] = None
    classification: Optional[str] = None
    config: dict = field(default_factory=dict)
    content: Optional[Union[dict, str]] = None
    depth_reference: str = "msl"
    description: Union[str, list] = ""
    display_name: Optional[str] = None
    fmu_context: Optional[str] = None
    forcefolder: str = ""
    grid_model: Optional[str] = None
    is_observation: bool = False
    is_prediction: bool = True
    name: str = ""
    undef_is_zero: bool = False
    parent: str = ""
    realization: Optional[int] = None  # deprecated
    rep_include: Optional[bool] = None
    reuse_metadata_rule: Optional[str] = None  # deprecated
    runpath: Optional[Union[str, Path]] = None
    subfolder: str = ""
    tagname: str = ""
    timedata: Optional[List[list]] = None
    unit: Optional[str] = ""
    verbosity: str = "DEPRECATED"  # remove in version 2
    vertical_domain: dict = field(default_factory=dict)
    workflow: Optional[Union[str, Dict[str, str]]] = None
    table_index: Optional[list] = None

    # some keys that are modified version of input, prepended with _use
    _usefmtflag: str = field(default="", init=False)

    # storing resulting state variables for instance, non-public:
    _metadata: dict = field(default_factory=dict, init=False)
    _pwd: Path = field(default_factory=Path, init=False)
    _config_is_valid: bool = field(default=True, init=False)
    _fmurun: bool = field(default=False, init=False)

    # Need to store these temporarily in variables until we stop
    # updating state of the class also on export and generate_metadata
    _classification: enums.AccessLevel = enums.AccessLevel.internal
    _rep_include: bool = field(default=False, init=False)

    # << NB! storing ACTUAL casepath:
    _rootpath: Path = field(default_factory=Path, init=False)

    def __post_init__(self) -> None:
        logger.info("Running __post_init__ ExportData")
        logger.debug("Global config is %s", prettyprint_dict(self.config))

        self._show_deprecations_or_notimplemented()

        self._fmurun = get_fmu_context_from_environment() != FmuContext.NON_FMU

        # set defaults for mutable keys
        self.vertical_domain = {"depth": "msl"}

        # if input is provided as an ENV variable pointing to a YAML file; will override
        if SETTINGS_ENVNAME in os.environ:
            warnings.warn(
                "Providing input settings through environment variables is deprecated, "
                "use ExportData(**yaml_load(<your_file>)) instead. To "
                "disable this warning, remove the 'FMU_DATAIO_CONFIG' env.",
            )

        # global config which may be given as env variable
        # will only be used if not explicitly given as input
        if not self.config and GLOBAL_ENVNAME in os.environ:
            self.config = some_config_from_env(GLOBAL_ENVNAME) or {}

        self._validate_and_establish_fmucontext()

        # check state of global config
        self._config_is_valid = global_configuration.is_valid(self.config)
        if self._config_is_valid:
            # TODO: This needs refinement: _config_is_valid should be removed
            self.config = global_configuration.roundtrip(self.config)
        else:
            warnings.warn(
                "The global config file is lacking key information, hence no metadata "
                "will be exported. Follow the simple 'Getting started' steps "
                "to do necessary preparations and enable metadata export: "
                "https://fmu-dataio.readthedocs.io/en/latest/preparations.html ",
                UserWarning,
            )

        self._classification = self._get_classification()
        self._rep_include = self._get_rep_include()

        self._pwd = Path().cwd()
        self._rootpath = self._establish_rootpath()
        logger.debug("pwd:   %s", str(self._pwd))
        logger.info("rootpath:   %s", str(self._rootpath))

        logger.info("Ran __post_init__")

    def _get_classification(self) -> enums.AccessLevel:
        """
        Get the security classification as an AccessLevel.
        The order of how the classification is set is:
        1. from classification argument if present
        2. from access_ssdl argument (deprecated) if present
        3. from access.classification in config (has been mirrored from
        access.ssdl.access_level if not present)

        """
        if self.classification is not None:
            logger.info("Classification is set from input")
            classification = self.classification

        elif self.access_ssdl and self.access_ssdl.get("access_level"):
            logger.info("Classification is set from access_ssdl input")
            classification = self.access_ssdl["access_level"]

        elif self._config_is_valid:
            logger.info("Classification is set from config")
            classification = self.config["access"]["classification"]
        else:
            # note the one below here will never be used, because that
            # means the config is invalid and no metadata will be produced
            logger.info("Using default classification 'internal'")
            classification = enums.AccessLevel.internal

        if enums.AccessLevel(classification) == enums.AccessLevel.asset:
            warnings.warn(
                "The value 'asset' for access.ssdl.access_level is deprecated. "
                "Please use 'restricted' in input arguments or global variables "
                "to silence this warning.",
                FutureWarning,
            )
            return enums.AccessLevel.restricted
        return enums.AccessLevel(classification)

    def _get_rep_include(self) -> bool:
        """
        Get the rep_include status.
        The order of how the staus is set is:
        1. from rep_include argument if present
        2. from access_ssdl argument (deprecated) if present
        3. from access.ssdl.rep_include in config
        4. default to False if not found
        """
        if self.rep_include is not None:
            logger.debug("rep_include is set from input")
            return self.rep_include

        if self.access_ssdl and self.access_ssdl.get("rep_include"):
            logger.debug("rep_include is set from access_ssdl input")
            return self.access_ssdl["rep_include"]

        if "rep_include" in self.config.get("access", {}).get("ssdl", {}):
            logger.debug("rep_include is set from config")
            return self.config["access"]["ssdl"]["rep_include"]

        logger.debug("Using default 'rep_include'=False")
        return False

    def _show_deprecations_or_notimplemented(self) -> None:
        """Warn on deprecated keys or on stuff not implemented yet."""

        if self.access_ssdl:
            warn(
                "The 'access_ssdl' argument is deprecated and will be removed in the "
                "future. Use the more explicit 'classification' and 'rep_include' "
                "arguments instead.",
                FutureWarning,
            )
            if self.classification is not None or self.rep_include is not None:
                raise ValueError(
                    "Using the 'classification' and/or 'rep_include' arguments, "
                    "in combination with the (legacy) 'access_ssdl' argument "
                    "is not supported."
                )

        if self.runpath:
            warn(
                "The 'runpath' key has currently no function. It will be evaluated for "
                "removal in fmu-dataio version 2. Use 'casepath' instead!",
                UserWarning,
            )

        if self.grid_model:
            warn(
                "The 'grid_model' key has currently no function. It will be evaluated "
                "for removal in fmu-dataio version 2.",
                UserWarning,
            )

        if self.legacy_time_format:
            warn(
                "Using the 'legacy_time_format=True' option to create metadata files "
                "with the old format for time is now deprecated. This option has no "
                "longer an effect and will be removed in the near future.",
                UserWarning,
            )
        if not self.createfolder:
            warn(
                "Using the 'createfolder=False' option is now deprecated. "
                "This option has no longer an effect and can safely be removed",
                UserWarning,
            )
        if not self.verifyfolder:
            warn(
                "Using the 'verifyfolder=False' option to create metadata files "
                "This option has no longer an effect and can safely be removed",
                UserWarning,
            )
        if self.reuse_metadata_rule:
            warn(
                "The 'reuse_metadata_rule' key is deprecated and has no effect. "
                "Please remove it from the argument list.",
                UserWarning,
            )
        if self.realization:
            warn(
                "The 'realization' key is deprecated and has no effect. "
                "Please remove it from the argument list.",
                UserWarning,
            )
        if self.table_include_index:
            warn(
                "The 'table_include_index' option is deprecated and has no effect. "
                "To get the index included in your dataframe, reset the index "
                "before exporting the dataframe with dataio i.e. df = df.reset_index()",
                UserWarning,
            )
        if self.verbosity != "DEPRECATED":
            warn(
                "Using the 'verbosity' key is now deprecated and will have no "
                "effect and will be removed in near future. Please remove it from the "
                "argument list. Set logging level from client script in the standard "
                "manner instead.",
                UserWarning,
            )
        if isinstance(self.workflow, dict):
            warn(
                "The 'workflow' argument should be given as a string. "
                "Support for dictionary will be deprecated.",
                FutureWarning,
            )
        if self.allow_forcefolder_absolute:
            warn(
                "Support for using an absolute path as 'forcefolder' is deprecated. "
                "Please remove it from the argument list.",
                UserWarning,
            )
        if self.include_ertjobs:
            warn(
                "The 'include_ertjobs' option is deprecated and should be removed.",
                UserWarning,
            )

    def _validate_and_establish_fmucontext(self) -> None:
        """
        Validate the given 'fmu_context' input. if not explicitly given it
        will be established based on the presence of ERT environment variables.
        """

        if self.fmu_context and self.fmu_context.lower() == "case_symlink_realization":
            raise ValueError(
                "fmu_context is set to 'case_symlink_realization', which is no "
                "longer a supported option. Recommended workflow is to export "
                "your data as preprocessed ouside of FMU, and re-export the data "
                "with fmu_context='case' using a PRE_SIMULATION ERT workflow. "
                "If needed, forward_models in ERT can be set-up to create symlinks "
                "out into the individual realizations.",
                UserWarning,
            )

        env_fmu_context = get_fmu_context_from_environment()
        logger.debug("fmu context from input is %s", self.fmu_context)
        logger.debug("fmu context from environment is %s", env_fmu_context)

        # use fmu_context from environment if not explicitly set
        if self.fmu_context is None:
            logger.info(
                "fmu_context is established from environment variables %s",
                env_fmu_context,
            )
            self.fmu_context = env_fmu_context
        else:
            self.fmu_context = FmuContext(self.fmu_context.lower())
        logger.info("FMU context is %s", self.fmu_context)

        if not self._fmurun and self.fmu_context != FmuContext.PREPROCESSED:
            logger.warning(
                "Requested fmu_context is <%s> but since this is detected as a non "
                "FMU run, the actual context is force set to <%s>",
                self.fmu_context,
                FmuContext.NON_FMU,
            )
            self.fmu_context = FmuContext.NON_FMU

        if self.fmu_context != FmuContext.CASE and env_fmu_context == FmuContext.CASE:
            warn(
                "fmu_context is set to 'realization', but unable to detect "
                "ERT runpath from environment variable. "
                "Did you mean fmu_context='case'?",
                UserWarning,
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
        if "config" in legals:
            del legals["config"]  # config cannot be updated

        if "config" in newsettings:
            raise ValueError("Cannot have 'config' outside instance initialization")

        for setting, value in newsettings.items():
            if _validate_variable(setting, value, legals):
                setattr(self, setting, value)
                logger.info("New setting OK for %s", setting)

        self._show_deprecations_or_notimplemented()
        self._validate_and_establish_fmucontext()
        self._rootpath = self._establish_rootpath()

    def _establish_rootpath(self) -> Path:
        """
        Establish the rootpath. The rootpath is the folder that acts as the
        base root for all relative output files. The rootpath is dependent on
        whether this is run in a FMU context via ERT and whether it's being
        run from inside or outside RMS.

        1: Running ERT: the rootpath will be equal to the casepath
        2: Running RMS interactively: The rootpath will be rootpath/rms/model
        3: When none of the above conditions apply, the rootpath value will be equal
           to the present working directory (pwd).
        """
        logger.info("Establish roothpath")
        logger.debug(
            "inside RMS flag is %s (actual: %s))", ExportData._inside_rms, INSIDE_RMS
        )
        assert isinstance(self.fmu_context, FmuContext)

        if self._fmurun and (
            casepath := FmuProvider(
                fmu_context=self.fmu_context,
                casepath_proposed=Path(self.casepath) if self.casepath else None,
            ).get_casepath()
        ):
            logger.info("Run from ERT")
            return casepath.absolute()

        if ExportData._inside_rms or INSIDE_RMS:
            logger.info("Run from inside RMS")
            ExportData._inside_rms = True
            return self._pwd.parent.parent.absolute().resolve()

        logger.info("Running outside FMU context, using pwd as roothpath")
        return self._pwd

    def _get_fmu_provider(self) -> FmuProvider:
        assert isinstance(self.fmu_context, FmuContext)
        return FmuProvider(
            model=self.config.get("model"),
            fmu_context=self.fmu_context,
            casepath_proposed=Path(self.casepath) if self.casepath else None,
            workflow=self.workflow,
        )

    # ==================================================================================
    # Public methods:
    # ==================================================================================

    def generate_metadata(
        self,
        obj: types.Inferrable,
        compute_md5: bool = True,
        **kwargs: object,
    ) -> dict:
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
        logger.info("KW args %s", kwargs)

        self._update_check_settings(kwargs)

        if isinstance(obj, (str, Path)):
            if self.casepath is None:
                raise TypeError("No 'casepath' argument provided")
            _future_warning_preprocessed()
            return ExportPreprocessedData(
                config=self.config,
                casepath=self.casepath,
                is_observation=self.is_observation,
            ).generate_metadata(obj)

        self._classification = self._get_classification()
        self._rep_include = self._get_rep_include()

        self._update_fmt_flag()
        fmudata = self._get_fmu_provider() if self._fmurun else None
        self._metadata = generate_export_metadata(
            obj, self, fmudata, compute_md5=compute_md5
        )

        logger.info("The metadata are now ready!")

        return deepcopy(self._metadata)

    def export(
        self,
        obj: types.Inferrable,
        return_symlink: bool = False,
        **kwargs: Any,
    ) -> str:
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
        if return_symlink:
            warnings.warn(
                "The return_symlink option is deprecated and can safely be removed."
            )
        if isinstance(obj, (str, Path)):
            self._update_check_settings(kwargs)
            if self.casepath is None:
                raise TypeError("No 'casepath' argument provided")
            _future_warning_preprocessed()
            return ExportPreprocessedData(
                config=self.config,
                casepath=self.casepath,
                is_observation=self.is_observation,
            ).export(obj)

        metadata = self.generate_metadata(obj, compute_md5=True, **kwargs)
        logger.info("Object type is: %s", type(obj))

        outfile = Path(metadata["file"]["absolute_path"])
        # create output folders if they don't exist
        outfile.parent.mkdir(parents=True, exist_ok=True)
        metafile = outfile.parent / f".{outfile.name}.yml"

        export_file(obj, outfile, flag=self._usefmtflag)
        logger.info("Actual file is:   %s", outfile)

        if self._config_is_valid:
            export_metadata_file(metafile, metadata, savefmt=self.meta_format)
            logger.info("Metadata file is: %s", metafile)
        else:
            warnings.warn("Data will be exported, but without metadata.", UserWarning)

        return str(outfile)
