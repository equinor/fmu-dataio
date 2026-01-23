"""Module for DataIO class.

The metadata spec is documented as a JSON schema, stored under schema/.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal

from fmu.dataio.aggregation import AggregatedData
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results import enums, global_configuration
from fmu.datamodels.fmu_results.enums import FMUContext
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._deprecations import (
    DeprecationError,
    _check_vertical_domain_dict,
    future_warning_preprocessed,
    resolve_deprecations,
)
from ._export_config import (
    ExportConfig,
    _resolve_classification,
    _resolve_content_enum,
    _resolve_content_metadata,
    _resolve_fmu_context,
    _resolve_rep_include,
    _resolve_vertical_domain,
)
from ._logging import null_logger
from ._metadata import generate_export_metadata
from ._runcontext import RunContext
from ._utils import (
    export_metadata_file,
    export_object_to_file,
    read_metadata_from_file,
    some_config_from_env,
)
from .case import CreateCaseMetadata
from .exceptions import ValidationError
from .manifest._manifest import update_export_manifest
from .preprocessed import ExportPreprocessedData
from .providers._fmu import FmuProvider
from .providers.objectdata._provider import (
    ObjectDataProvider,
    objectdata_provider_factory,
)

if TYPE_CHECKING:
    from fmu.datamodels.fmu_results.standard_result import StandardResult

    from . import types


GLOBAL_ENVNAME: Final = "FMU_GLOBAL_CONFIG"
SETTINGS_ENVNAME: Final = (
    "FMU_DATAIO_CONFIG"  # Feature deprecated, still used for user warning.
)

logger: Final = null_logger(__name__)

AggregatedData: Final = AggregatedData  # Backwards compatibility alias
CreateCaseMetadata: Final = CreateCaseMetadata  # Backwards compatibility alias


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
    """This class provides context for the metadata generated when data is exported.

    Here is a complete example of how it is used:

    .. code-block:: python

       for name in ["TopOne", "TopTwo", "TopThree"]:
           poly = xtgeo.polygons_from_roxar(project, name, POL_FOLDER)

           ed = dataio.ExportData(
               config=CFG,
               content="depth",
               unit="m",
               vertical_domain="fault_lines",
               domain_reference="msl",
               timedata=None,
               is_observation=False,
               tagname="faultlines",
               workflow="rms structural model",
               name=name
           )
           out = ed.export(poly)


    In general, fmu-dataio tries to take care of exporting data automatically to
    conventional and standard locations. In the documentation below you might find
    references to the following terms.

    ``pwd``
       The present working directory. This is the directory a script or application is
       started from.

    ``rootpath``
       The directory from which relative file names are relative to. This is
       auto-detected by fmu-dataio.

    ``casepath``
       The path where the FMU case originates from (is started from). This should be
       equivalent to the ``rootpath`` in most circumstances.

    Examples:

    .. code-block:: shell

       /project/foo/resmod/ff/2022.1.0/rms/model                   # pwd
       /project/foo/resmod/ff/2022.1.0/                            # rootpath

    A file:

    .. code-block:: shell

       /project/foo/resmod/ff/2022.1.0/share/results/maps/xx.gri   # example absolute
                                       share/results/maps/xx.gri   # example relative

    When running an Ert forward job using a normal Ert job (e.g. a script):

    .. code-block:: shell

       /scratch/nn/case/realization-44/iter-2                      # pwd
       /scratch/nn/case                                            # rootpath

    A file:

    .. code-block:: shell

       /scratch/nn/case/realization-44/iter-2/share/results/maps/xx.gri  # absolute
                        realization-44/iter-2/share/results/maps/xx.gri  # relative

    When running an Ert forward job but here executed from RMS:

    .. code-block:: shell

       /scratch/nn/case/realization-44/iter-2/rms/model            # pwd
       /scratch/nn/case                                            # rootpath

    A file:

    .. code-block:: shell

       /scratch/nn/case/realization-44/iter-2/share/results/maps/xx.gri  # absolute
                        realization-44/iter-2/share/results/maps/xx.gri  # relative

    """

    # ----------------------------------------------------------------------------------
    #
    # This role for this class is to be:
    # - public (end user) interface
    # - collect the full settings from global config, user keys and class variables
    # - process and validate these settings
    # - establish PWD and rootpath
    #
    # Then other classes will further do the detailed metadata processing, cf _MetaData
    # and subsequent classes called by _MetaData
    #
    # ----------------------------------------------------------------------------------

    # ##################################################################################

    # ----------------------------------------------------------------------------------
    #
    # Required input values to create metadata. These should be ordered from Required
    # parameters first, and in order of importance, as they will be rendered in the
    # documentation in the order listed here.
    #
    # ----------------------------------------------------------------------------------

    config: dict | GlobalConfiguration = field(default_factory=dict)
    """Required in order to produce valid metadata.

    This global config must be provided either as an input value here or through an
    environment variable.

    This value should be a dictionary with static settings. In the standard case
    this is read from FMU global variables produced by ``fmuconfig``. The dictionary
    must contain some predefined main level keys to work with fmu-dataio.

    .. note::
       If missing or empty, an :meth:`export` may still be done, but without any
       metadata produced.

    """

    content: str | dict | None = None
    """A required string describing the content of the data, e.g. ``"volumes"``.

    .. warning::
       Using the ``content`` argument as a ``dict`` to set both the content and the
       content metadata will be deprecated. Set the ``content`` argument to a valid
       content string, and provide the extra information through the
       :attr:`content_metadata` argument instead.

    Some content types, like ``"seismic"``, require additional information. This should
    be provided through the :attr:`content_metadata` argument described below.

    The list of content types that can be provided is controlled and input values are
    validated against a current list of them. In the following enumeration you would use
    **only** the string values of the content type.

    .. autoclass:: fmu.datamodels.fmu_results.enums.Content
       :members:
       :exclude-members: __new__, parameters
       :no-index:
       :no-special-members:

    """
    # ^ parameters is specially excluded to discourage users from attempting this
    # It is handled automatically.

    content_metadata: dict | None = None
    """Optional. Dictionary with additional information about the provided content. Only
    required for some :attr:`content` types, e.g. ``"seismic"``.

    Example:

    .. code-block:: python

       content_metadata={"attribute": "amplitude", "calculation": "mean"},

    """

    classification: str | None = None
    """Optional. Security classification level of the data object.

    If present it will override the default found in the config.

    The list of classification types that can be provided is controlled and input values
    are validated against a current list of them. In the following enumeration you would
    use **only** the string values of the classification type.

    .. autoclass:: fmu.datamodels.common.enums.Classification
       :members:
       :exclude-members: __new__
       :no-index:
       :no-special-members:

    """

    domain_reference: str = "msl"
    """Optional. Reference to the vertical scale of the data.

    The list of classification types that can be provided is controlled and input values
    are validated against a current list of them. In the following enumeration you would
    use **only** the string values of the classification type.

    .. autoclass:: fmu.datamodels.fmu_results.enums.DomainReference
       :members:
       :exclude-members: __new__
       :no-index:
       :no-special-members:

    .. note:: Use the :attr:`vertical_domain` key to set the domain (depth or time).

    """

    vertical_domain: str | dict = "depth"
    """Optional. The vertical domain of the data.

    The list of classification types that can be provided is controlled and input values
    are validated against a current list of them. In the following enumeration you would
    use **only** the string values of the classification type.

    .. autoclass:: fmu.datamodels.fmu_results.enums.VerticalDomain
       :members:
       :exclude-members: __new__
       :no-index:
       :no-special-members:

    A reference for the vertical scale can be provided with the
    :attr:`domain_reference` value.

    .. note::
       If the :attr:`content` is ``"depth"`` or ``"time"`` this value will be set
       accordingly.

    .. warning::
       Providing a dictionary as a value is deprecated.

    """

    geometry: str | None = None
    """Optional. For grid properties **only** which need a reference to the 3D grid
    geometry object.

    The value must point to an existing file which has already been exported with
    fmu-dataio, and hence has an associated metadata file. The grid name will be derived
    from the grid metadata, if present, and applied as part of the grid property file
    name.

    .. note::
       This value may replace the usage of both the :attr:`parent` value and the
       ``grid_model`` value in the near future.

    """

    is_observation: bool = False
    """If ``True`` then data will be exported to the ``share/observations/`` directory.

    By default this is ``False`` which will export results to the ``share/results/``
    directory.

    However, if :attr:`preprocessed` is ``True``, then the export directory will be set
    to ``share/preprocessed/`` irrespective the value of :attr:`is_observation`.
    """

    is_prediction: bool = True
    """Indicates if the exported data is model prediction data."""

    timedata: list[str] | list[list[str]] | None = None
    """Optional. List of dates, where the dates are strings on form ``"YYYYMMDD"``.

    .. code-block:: python

       timedata=["20200101"],


    .. code-block:: python

       timedata=["20200101", "20180101"],

    A maximum of two dates can be input. The oldest date will be set as ``t0`` in the
    metadata and the latest date will be ``t1``.

    .. note::

       It is also possible to provide a label to each date by using a list of lists,
       e.g. ``[["20200101", "monitor"], ["20180101", "base"]]``.

    """

    unit: str | None = ""
    """Optional. The measurement unit relevant to the exported data.

    For example, ``"m"`` would be set if the measurement unit is meters.

    .. caution::
       This value is not currently controlled by a known list but will be in the future.

    """

    table_index: list[str] | None = None
    """Optional. A list of strings indicating the index columns for tabular data.

    This value should be set for tabular data like Pandas data frames **only**.

    Example:

    .. code-block::

       table_index=["ZONE", "REGION"],

    This can also be applied to points or polygons objects that are exported in table
    format to specify attributes that should act as index columns.

    .. tip::
       Index columns in tabular data refer to one or more columns that uniquely identify
       each row in the dataset. They serve as a reference point for data retrieval and
       manipulation, enabling simple and efficient access to specific rows.

    """

    preprocessed: bool = False
    """If True, data is exported to the ``"share/preprocessed/"`` directory.

    This metadata can be partially re-used in an Ert model run using the
    ``ExportPreprocessedData`` class.

    .. note::
       Most data are not preprocessed data, and as such this key shouldn't often be
       used. An example of preprocessed data is seismic data.

    """

    description: str | list[str] = ""
    """Optional. A multi-line description of the data either as a string or a list of
    strings.

    .. tip::
       You do not need to set this.

    """

    display_name: str | None = None
    """Optional. Set a display name for clients to use when visualizing.

    .. tip::
       You do not need to set this.

    """

    name: str = ""
    """Optional. The name of the data object being exported.

    If not set, fmu-dataio infers it from object data type. If the name is found in the
    ``stratigraphy`` static metadata list, the official stratigraphic name will be used.

    For example, if ``"TopValysar"`` is the model name and the actual name is ``"Valysar
    Top Fm."``, the latter name will be used.

    .. tip::
       You do not need to set this.

    """

    tagname: str = ""
    """Optional. A short tag description which will be a part of the file name.

    As an example, if exporting a fault polygon from a horizon named ``"TopVolantis"``,

    .. code-block:: python

       tagname="faultlines",

    The exported filename will be ``volantis_gp_top--faultlines.csv``

    .. tip::
       You do not need to set this, but it may be useful for local workflows.

    """

    workflow: str | dict[str, str] | None = None
    """Optional. Short string description of workflow.

    .. warning::
       Providing a dictionary as a value is deprecated.

    .. tip::
       You do not need to set this.

    """

    forcefolder: str = ""
    """Optional. This value allows exporting to a non-standard directory relative to
    the casepath/rootpath.

    .. warning::
       Using this optional is generally not recommended.

    This option is dependent upon the FMU context (case or realization) and the
    :attr:`is_observation` boolean value.

    Example:

    .. code-block:: python

       forcefolder="seismic",

    This will replace the ``cubes/`` standard directory for ``xtgeo.Cube`` output with
    ``seismic/``.

    .. caution::
       Use with care and avoid if possible!

    """

    parent: str = ""
    """Optional. This value is required for datatype ``xtgeo.GridProperty``, unless the
    :attr:`geometry` value is given.

    "Parent" refers to the name of the grid geometry. It will only be added in the
    filename, and not as genuine metadata entry.

    .. warning::
       This value is a candidate for deprecation. Use :attr:`geometry` instead.

    If both :attr:`parent` and :attr:`geometry` are given, the grid name derived from
    the :attr:`geometry` object will have precedence.
    """

    casepath: str | Path | None = None
    """Optional. Path to a case directory that contains valid case metadata
    ``fmu_case.yml`` in folder ``<CASE_DIR>/share/metadata/``.

    .. tip::
       You typically do not need to set this.

    """

    # ----------------------------------------------------------------------------------
    #
    # Undocumented members.
    #
    # These are not yet deprecated, but are not encouraged for use. Convert the doc
    # string to a comment to prevent it from rendering in the documentation.
    #
    # ----------------------------------------------------------------------------------

    aggregation: bool = False
    # Does not appear to have been used for anything.

    fmu_context: str | None = None
    # Optional string with value ``realization`` or ``case``.
    #
    # .. tip::
    #    You most likely do not need to set this. fmu-dataio infers this by itself.
    #
    # If not explicitly given it will be inferred based on the presence of Ert
    # environment variables.
    #
    # If ``fmu_context="realization"`` fmu-dataio will export data per realization, and
    # should be used in normal Ert forward models.
    #
    # If ``fmu_context="case"`` fmu-dataio will export data relative to the case
    # directory. When specifying the case context the ``casepath`` must provided through
    # the ``casepath`` value.

    rep_include: bool | None = None
    # Optional. If True then the data object will be available in REP.

    subfolder: str = ""
    # Set subfolders for file output. The input should be a string representing a
    # relative path of at least one additional directory.

    undef_is_zero: bool = False
    # Flags that NaNs should be considered as zero in aggregations.

    # ----------------------------------------------------------------------------------
    #
    # Deprecated members.
    #
    # Convert the doc string to a comment, or remove it, to prevent it from rendering in
    # the documentation.
    #
    # ----------------------------------------------------------------------------------

    access_ssdl: dict = field(default_factory=dict)  # deprecated
    depth_reference: str | None = None  # deprecated
    realization: int | None = None  # deprecated
    reuse_metadata_rule: str | None = None  # deprecated
    runpath: str | Path | None = None  # Deprecated. Issues warning.
    verbosity: str = "DEPRECATED"  # remove in version 2
    grid_model: str | None = None

    # Class variables

    allow_forcefolder_absolute: ClassVar[bool] = False  # deprecated
    arrow_fformat: ClassVar[str | None] = None  # deprecated and no effect
    case_folder: ClassVar[str] = "share/metadata"
    createfolder: ClassVar[bool] = True  # deprecated
    cube_fformat: ClassVar[str | None] = None  # deprecated and no effect
    filename_timedata_reverse: ClassVar[bool] = False  # reverse order output file name
    grid_fformat: ClassVar[str | None] = None  # deprecated and no effect
    include_ertjobs: ClassVar[bool] = False  # deprecated
    legacy_time_format: ClassVar[bool] = False  # deprecated
    meta_format: ClassVar[Literal["yaml", "json"] | None] = None  # deprecated
    polygons_fformat: ClassVar[str] = "csv"  # or use "csv|xtgeo"
    points_fformat: ClassVar[str] = "csv"  # or use "csv|xtgeo"
    surface_fformat: ClassVar[str | None] = None  # deprecated and no effect
    table_fformat: ClassVar[str] = "csv"
    dict_fformat: ClassVar[str | None] = None  # deprecated and no effect
    table_include_index: ClassVar[bool] = False  # deprecated
    verifyfolder: ClassVar[bool] = True  # deprecated

    # ----------------------------------------------------------------------------------
    #
    # Stateful members.
    #
    # Need to store these temporarily in variables until we stop updating state of the
    # class also on export and generate_metadata
    #
    # ----------------------------------------------------------------------------------

    _resolved_fmu_context: FMUContext | None = None
    _resolved_preprocessed: bool = False
    _resolved_vertical_domain: str = field(default="depth", init=False)
    _resolved_domain_reference: str = field(default="msl", init=False)
    _classification: Classification = Classification.internal
    _rep_include: bool = field(default=False, init=False)
    _initialized: bool = field(default=False, init=False, repr=False)
    _cached_export_config: ExportConfig | None = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        logger.info("Running __post_init__ ExportData")

        self._resolve_deprecations()

        # if input is provided as an ENV variable pointing to a YAML file; will override
        if SETTINGS_ENVNAME in os.environ:
            warnings.warn(
                "Providing input settings through environment variables is deprecated, "
                "use ExportData(**yaml_load(<your_file>)) instead. To "
                "disable this warning, remove the 'FMU_DATAIO_CONFIG' env.",
                FutureWarning,
            )

        # global config which may be given as env variable
        # will only be used if not explicitly given as input
        if not self.config and GLOBAL_ENVNAME in os.environ:
            self.config = some_config_from_env(GLOBAL_ENVNAME) or {}

        self._cached_export_config = ExportConfig.from_export_data(self)

        # TODO: Remove everything below when no dependency on them
        self._resolved_fmu_context, self._resolved_preprocessed = _resolve_fmu_context(
            self.fmu_context, self.preprocessed
        )
        self._resolved_vertical_domain, self._resolved_domain_reference = (
            _resolve_vertical_domain(self.vertical_domain, self.domain_reference)
        )

        try:
            self.config = GlobalConfiguration.model_validate(self.config)
        except global_configuration.ValidationError as e:
            if "masterdata" not in self.config:
                warnings.warn(
                    "The global config file is lacking masterdata definitions, hence "
                    "no metadata will be exported. Follow the simple 'Getting started' "
                    "steps to do necessary preparations and enable metadata export: "
                    "https://fmu-dataio.readthedocs.io/en/latest/getting_started.html ",
                    UserWarning,
                )
            else:
                global_configuration.validation_error_warning(e)
            self.config = {}

        self._classification = _resolve_classification(
            self.classification,
            self.access_ssdl,
            self.config if isinstance(self.config, GlobalConfiguration) else None,
        )
        self._rep_include = _resolve_rep_include(
            self.rep_include,
            self.access_ssdl,
            self.config if isinstance(self.config, GlobalConfiguration) else None,
        )
        self._runcontext = self._get_runcontext()

        object.__setattr__(self, "_initialized", True)
        logger.info("Ran __post_init__")

    def __setattr__(self, name: str, value: Any) -> None:
        """Catch attribute mutations and warn."""
        is_initialized = getattr(self, "_initialized", False)

        if is_initialized and not name.startswith("_") and name != "config":
            warnings.warn(
                f"Mutating ExportData.{name} after initialization is deprecated "
                "and will be removed in a future version. Create a new ExportData "
                "instance with the desired values instead.",
                FutureWarning,
            )

        # Invalidate cached config when public properties change. It needs to be
        # re-created with the new values.
        object.__setattr__(self, "_cached_export_config", None)

        object.__setattr__(self, name, value)

        if name == "vertical_domain":
            maybe_warnings = _check_vertical_domain_dict(value)
            for warning, category in maybe_warnings:
                warnings.warn(warning, category)

        # TODO: Remove this when codebase reads from ExportConfig
        if name in ("vertical_domain", "domain_reference"):
            resolved_vertical_domain, resolved_domain_reference = (
                _resolve_vertical_domain(
                    getattr(self, "vertical_domain"),  # noqa: B009
                    getattr(self, "domain_reference"),  # noqa: B009
                )
            )
            object.__setattr__(
                self, "_resolved_vertical_domain", resolved_vertical_domain
            )
            object.__setattr__(
                self, "_resolved_domain_reference", resolved_domain_reference
            )

    def _get_runcontext(self) -> RunContext:
        """Get the run context for this ExportData instance."""
        casepath_proposed = Path(self.casepath) if self.casepath else None
        return RunContext(casepath_proposed, fmu_context=self._resolved_fmu_context)

    def _get_content_enum(self) -> enums.Content | None:
        """Get the content enum."""
        return _resolve_content_enum(self.content)

    def _get_content_metadata(self) -> dict | None:
        """
        Get the content metadata if provided by as input, else return None.
        Validation takes place in the objectdata provider.
        """
        return _resolve_content_metadata(self.content_metadata, self.content)

    def _resolve_deprecations(self) -> None:
        """Resolve deprecated arguments and emit warnings.

        Raises:
            DeprecationError: If invalid argument combinations are detected.
        """
        resolution = resolve_deprecations(
            # Arguments with replacements
            access_ssdl=self.access_ssdl or None,
            classification=self.classification,
            rep_include=self.rep_include,
            content=self.content,
            vertical_domain=self.vertical_domain,
            workflow=self.workflow,
            # Arguments with no effect
            runpath=self.runpath,
            grid_model=self.grid_model,
            legacy_time_format=self.legacy_time_format,
            createfolder=self.createfolder,
            verifyfolder=self.verifyfolder,
            reuse_metadata_rule=self.reuse_metadata_rule,
            realization=self.realization,
            aggregation=self.aggregation,
            table_include_index=self.table_include_index,
            verbosity=self.verbosity,
            allow_forcefolder_absolute=self.allow_forcefolder_absolute,
            include_ertjobs=self.include_ertjobs,
            depth_reference=self.depth_reference,
            meta_format=self.meta_format,
            # Format options
            arrow_fformat=self.arrow_fformat,
            cube_fformat=self.cube_fformat,
            grid_fformat=self.grid_fformat,
            surface_fformat=self.surface_fformat,
            dict_fformat=self.dict_fformat,
        )

        for message, category in resolution.warnings:
            warnings.warn(message, category)

        if resolution.errors:
            raise DeprecationError("\n".join(resolution.errors))

    def _update_check_settings(self, newsettings: dict) -> None:
        """Update instance settings (properties) from other routines."""
        # if no newsettings (kwargs) this routine is not needed
        if not newsettings:
            return

        warnings.warn(
            "In the future it will not be possible to enter following arguments "
            f"inside the export() / generate_metadata() methods: {list(newsettings)}. "
            "Please move them up to initialization of the ExportData instance.",
            FutureWarning,
        )
        logger.info("Try new settings %s", newsettings)

        if "config" in newsettings:
            raise ValueError("Cannot have 'config' outside instance initialization")

        available_arguments = [field.name for field in fields(ExportData)]
        for setting, value in newsettings.items():
            if setting not in available_arguments:
                logger.warning("Unsupported key, raise an error")
                raise ValidationError(f"The input key '{setting}' is not supported")

            setattr(self, setting, value)
            logger.info("New setting OK for %s", setting)

        self._resolve_deprecations()
        self._resolved_fmu_context, self._resolved_preprocessed = _resolve_fmu_context(
            self.fmu_context, self.preprocessed
        )
        self._resolved_vertical_domain, self._resolved_domain_reference = (
            _resolve_vertical_domain(self.vertical_domain, self.domain_reference)
        )

        self._runcontext = self._get_runcontext()
        self._classification = _resolve_classification(
            self.classification,
            self.access_ssdl,
            self.config if isinstance(self.config, GlobalConfiguration) else None,
        )
        self._rep_include = _resolve_rep_include(
            self.rep_include,
            self.access_ssdl,
            self.config if isinstance(self.config, GlobalConfiguration) else None,
        )

        # Values have changed, so we need a new configuration.
        self._cached_export_config = ExportConfig.from_export_data(self)

    def _export_without_metadata(self, obj: types.Inferrable) -> str:
        """
        Export the object without a metadata file. The absolute export path
        is found using the FileDataProvider directly.
        A string with full path to the exported item is returned.
        """
        objdata = objectdata_provider_factory(obj, self)

        absolute_path = self._runcontext.exportroot / objdata.share_path

        export_object_to_file(absolute_path, objdata.export_to_file)
        return str(absolute_path)

    def _export_with_standard_result(
        self, obj: types.Inferrable, standard_result: StandardResult
    ) -> str:
        """Export the object with standard result information in the metadata."""

        if not isinstance(self.config, GlobalConfiguration):
            raise ValidationError(
                "When exporting standard_results it is required to have a valid config."
            )

        objdata = objectdata_provider_factory(obj, self, standard_result)
        metadata = self._generate_export_metadata(objdata)

        outfile = Path(metadata["file"]["absolute_path"])
        metafile = outfile.parent / f".{outfile.name}.yml"

        export_object_to_file(outfile, objdata.export_to_file)
        logger.info("Actual file is:   %s", outfile)

        export_metadata_file(metafile, metadata)

        if self._runcontext.inside_fmu:
            update_export_manifest(outfile, casepath=self._runcontext.casepath)

        return str(outfile)

    def _generate_export_metadata(self, objdata: ObjectDataProvider) -> dict[str, Any]:
        """Generate metadata for the provided ObjectDataProvider"""
        fmudata = (
            FmuProvider(
                runcontext=self._runcontext,
                model=(
                    self.config.model
                    if isinstance(self.config, GlobalConfiguration)
                    else None
                ),
                workflow=self.workflow,
                object_share_path=objdata.share_path,
            )
            if self._runcontext.inside_fmu
            else None
        )

        return generate_export_metadata(
            objdata=objdata,
            dataio=self,
            fmudata=fmudata,
        ).model_dump(mode="json", exclude_none=True, by_alias=True)

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
            compute_md5: Deprecated, a MD5 checksum will always be computed.
            **kwargs: Using other ExportData() input keys is now deprecated, input the
                arguments when initializing the ExportData() instance instead.

        Returns:
            A dictionary with all metadata.
        """

        logger.info("Generate metadata...")
        logger.info("KW args %s", kwargs)

        if not isinstance(self.config, GlobalConfiguration):
            warnings.warn(
                "From fmu.dataio version 3.0 it will not be possible to produce "
                "metadata when the global config is invalid.",
                FutureWarning,
            )

        if not compute_md5:
            warnings.warn(
                "Using the 'compute_md5=False' option to prevent an MD5 checksum "
                "from being computed is now deprecated. This option has no longer "
                "an effect and will be removed in the near future.",
                UserWarning,
            )

        self._update_check_settings(kwargs)

        if isinstance(obj, str | Path):
            if self.casepath is None:
                raise TypeError("No 'casepath' argument provided")
            future_warning_preprocessed()
            return ExportPreprocessedData(
                casepath=self.casepath,
                is_observation=self.is_observation,
            ).generate_metadata(obj)

        objdata = objectdata_provider_factory(obj, self)
        return self._generate_export_metadata(objdata)

    def export(
        self,
        obj: types.Inferrable,
        **kwargs: Any,
    ) -> str:
        """Export supported data objects with metadata.

        This function exports data without changing the *content* of the data. The *file
        format* of the data may be determined by values set in the class.

        A file containing metadata will be exported next to it. It will have the same
        name as the data, but will be prefixed with a `.`. This causes the metadata to
        not be visible by a standard `ls` command. The metadata is stored in a YAML
        file.

        .. code-block:: shell

           top_volantis--depth.gri
           .top_volantis--depth.gri.yml

        Args:
            obj: An xtgeo object, Pandas dataframe, or other supported object. A full
              list of supported data types can be found in the documentation.

        Returns:
            str: The full path to the exported item.

        Note:
            Providing ``**kwargs`` is deprecated and will be removed in a later version.
        """
        if "return_symlink" in kwargs:
            warnings.warn(
                "The return_symlink option is deprecated and can safely be removed."
            )
        if isinstance(obj, str | Path):
            self._update_check_settings(kwargs)
            if self.casepath is None:
                raise TypeError("No 'casepath' argument provided")
            future_warning_preprocessed()
            return ExportPreprocessedData(
                casepath=self.casepath,
                is_observation=self.is_observation,
            ).export(obj)

        logger.info("Object type is: %s", type(obj))
        self._update_check_settings(kwargs)

        # should only export object if config is not valid
        if not isinstance(self.config, GlobalConfiguration):
            warnings.warn("Data will be exported, but without metadata.", UserWarning)
            return self._export_without_metadata(obj)

        objdata = objectdata_provider_factory(obj, self)
        metadata = self._generate_export_metadata(objdata)

        outfile = Path(metadata["file"]["absolute_path"])
        metafile = outfile.parent / f".{outfile.name}.yml"

        export_object_to_file(outfile, objdata.export_to_file)
        logger.info("Actual file is:   %s", outfile)

        export_metadata_file(metafile, metadata)
        logger.info("Metadata file is: %s", metafile)

        if self._runcontext.inside_fmu:
            update_export_manifest(outfile, casepath=self._runcontext.casepath)

        return str(outfile)
