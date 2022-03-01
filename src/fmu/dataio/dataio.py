"""Module for DataIO class.

The metadata spec is documented as a JSON schema, stored under schema/.

The processing is based on handling first level keys which are

* Scalar special::

    $schema      |
    version      |     hard set in code, corresponding to schema version
    source       |

* ``class``        - determined by datatype, inferred

* Nested attributes::

    file         - information about the data object origin as file on disk
    tracklog     - events recorded on these data
    data         - about the data (see class). Inferred from input, data + fmuconfig
    display      - Deduced mostly from fmuconfig (TODO: issue on wait)
    fmu          - Deduced from fmuconfig and ERT
    access       - Govern permissions for exported data, infer from fmuconfig or args
    masterdata   - Static, infer from fmuconfig

"""
import datetime
import getpass
import json
import logging
import os
import pathlib
import re
import sys
import uuid
import warnings
from collections import OrderedDict
from typing import Any, List, Optional, Union

import deprecation
import yaml

from . import _utils
from ._export_item import _ExportItem
from .version import version

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# the word "DOLLARS" refers losely to $schema and related keys (version, source)
DOLLARS = OrderedDict(
    [
        (
            "$schema",
            "https://main-fmu-schemas-dev.radix.equinor.com/schemas/0.8.0/"
            "fmu_results.json",
        ),
        (
            "version",
            "0.8.0",
        ),
        (
            "source",
            "fmu",
        ),
    ]
)


# ######################################################################################
# ExportData
# ######################################################################################


class ExportData:
    """Class for exporting data with rich metadata in FMU.

    This class sets up the general metadata content to be applied in export. The idea
    is that one ExportData instance can be re-used for several similar export() jobs.
    For example::

        edata = dataio.ExportData(
            config=CFG,
            content="depth",
            unit="m",
            vertical_domain={"depth": "msl"},
            timedata=None,
            is_prediction=True,
            is_observation=False,
            tagname="faultlines",
            workflow="rms structural model",
        )

        for name in ["TopOne", TopTwo", "TopThree"]:
            poly = xtgeo.polygons_from_roxar(PRJ, hname, POL_FOLDER)
            out = ed.export(poly, name=name)

    Some keyword settings like ``name``, ``tagname`` etc can be set in both the
    ExportData instance and directly in the ``export()`` function, to provide
    flexibility for different use cases. If both are set, the ``export()`` setting
    will win.


    Args:
        runpath: The relative location of the current run root. This is optional and
            will in most cased be auto-detected, assuming that FMU folder conventions
            are followed. For an ERT run e.g. /scratch/xx/nn/case/realization-0/iter-0/.
            while in a revision at project disc it will the revision root e.g.
            /project/xx/resmod/ff/21.1.0/.
        context: [EXPERIMENTAL] The context of the object with respect to
            itself and/or other stratigraphic units. The default is None, but for
            e.g. seismic attributes this can be important. The input is a
            dictionary with the following fields: [TODO]
        config: A configuation dictionary. In the standard case this is read
            from FMU global variables (via fmuconfig). The dictionary must contain
            some predefined main level keys to work with fmu-dataio. If the key is
            missing or key value is None, then it will look for the environment variable
            FMU_GLOBAL_CONFIG to detect the file. If no success in finding the file,
            a UserWarning is made.
        content: Is a string or a dictionary with one key. Example is "depth" or
            {"fluid_contact": {"xxx": "yyy", "zzz": "uuu"}}
        subfolder: It is possible to set one level of subfolders for file output.
            The input should only accept a single folder name, i.e. no paths. If
            paths are present, a deprecation warning will be raised.
        forcefolder: This setting shall only be used as exception, and will make it
            possible to output to a non-standard folder. A ``/`` in front will indicate
            an absolute path; otherwise it will be relative to RUNPATH. Use with care.
        include_index: This applies to Pandas (table) data only, and if True then the
            index column will be exported.
        vertical_domain: This is dictionary with a key and a reference e.g.
            {"depth": "msl"} which is default (if None is input)
        timedata: If given, a list of lists with dates, .e.g.
            [[20200101, "monitor"], [20180101, "base"]] or just [[20210101]]
        is_prediction: True (default) of model prediction data
        is_observation: Default is False. If True, then disk storage will be on the
            "share/observations" folder
        workflow: Short tag desciption of workflow (as description)
        casepath: Absolute path to the case root. If not provided, it will be attempted
            parsed from the file structure.

        name: The name of the object. If not set it is tried to be inferred from
            the xtgeo/pandas/... object. The name is then checked towards the
            stratigraphy list, and name is replaced with official stratigraphic
            name if found in static metadata `stratigraphy`. For example, if
            "TopValysar" is the model name and the actual name
            is "Valysar Top Fm." that latter name will be used.
        unit: Is the unit of the exported item(s), e.g. "m" or "fraction".
        parent: This key is required for datatype GridProperty, and refers to the
            name of the grid geometry.
        tagname: This is a short tag description which be be a part of file name.
        description: A multiline description of the data.
        access_ssdl: A dictionary that will overwrite or append to the default ssdl
            settings read from the config. Example:
            ``{"access_level": "restricted", "rep_include": False}``
        display_name: Set name for clients to use when visualizing.

        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO".
        **kwargs: For special developer settings
    """

    surface_fformat = "irap_binary"
    table_fformat = "csv"
    arrow_fformat = "arrow"
    polygons_fformat = "csv"  # or use "csv|xtgeo" to avoid renaming of xtgeo columns
    points_fformat = "csv"  # or use "csv|xtgeo" to avoid renaming of xtgeo columns
    grid_fformat = "roff"
    cube_fformat = "segy"

    # this is case folder which is "outside runs" i.e. another relative!
    # e.g. /somepath/mycase/share/metadata
    case_folder = "share/metadata"

    createfolder = True
    meta_format = "yaml"

    def __init__(
        self,
        runpath: Optional[str] = None,
        access_ssdl: Optional[dict] = None,
        config: Optional[dict] = None,
        content: Optional[Union[str, dict]] = None,
        context: Optional[dict] = None,
        is_prediction: Optional[bool] = True,
        is_observation: Optional[bool] = False,
        subfolder: Optional[str] = None,
        forcefolder: Optional[str] = None,
        timedata: Optional[list] = None,
        include_index: Optional[bool] = False,
        vertical_domain: Optional[dict] = None,
        workflow: Optional[Union[str, dict]] = None,
        # the following keys can be overridden in the export() function:
        name: Optional[str] = None,
        parent: Optional[dict] = None,
        tagname: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[List[str]] = None,
        unit: Optional[str] = None,
        verbosity: Optional[str] = "CRITICAL",
        **kwargs,  # developer options
    ) -> None:
        # kwargs:
        #    runfolder: Override _pwd (process working directory) and this a developer
        #        developer setting when running tests e.g. in pytest's tmp_path
        #    dryrun: Set instance variables but do not run functions (for unit testing)
        #    inside_rms: If forced to true then pretend to be in rms env.
        self._verbosity = verbosity
        logger.setLevel(level=self._verbosity)
        self._runpath = runpath
        self._access_ssdl = access_ssdl
        self._config = self._config_get(config)
        self._content = content
        self._context = context
        self._is_prediction = is_prediction
        self._is_observation = is_observation
        self._timedata = timedata
        self._vertical_domain = (
            {"depth": "msl"} if vertical_domain is None else vertical_domain
        )
        self._subfolder = self._check_subfolder(subfolder)
        self._include_index = include_index
        self._workflow = workflow

        # the following may change quickly in e.g. a loop and can be overridden
        # in export():
        self._name = name
        self._parent = parent
        self._tagname = tagname
        self._display_name = display_name
        self._description = description
        self._unit = unit

        # keep track of case
        # TODO: Need to differentiate the different usages of "case"
        # Here, the _case refers to case metadata
        self._case = False

        # keep track of this is an FMU run or not. FMU run here refers to the FORWARD
        # context (realization ran by ERT)
        self._is_fmurun = None

        # store placeholder for ERT information
        self._ert = OrderedDict()

        # store iter and realization names, paths and ids (when running ERT)
        self._itername = None  # name of the folder, e.g. "iter-0"
        self._realname = None  # name of the folder, e.g. "realization-0"
        self._iterpath = None  # path to the iteration
        self._realpath = None  # path to the realization
        self._iteration_id = None  # id of the iteration, e.g. "0"
        self._realization_id = None  # id of the realization, e.g. "0"

        # store case root and uuid
        self._casepath = None
        self._case_uuid = None

        # run private method for processing the pwd
        self._process_pwd_runpath(kwargs)

        # need to set/check forcefolder after RUNPATH is set:
        self._forcefolder = self._check_forcefolder(forcefolder)

        # define chunks of metadata for primary first order categories
        # (except class which is set directly later)
        self.metadata4strat = None
        self.metadata4dollars = DOLLARS  # schema, version, source
        self.metadata4file = OrderedDict()  # file (to be populated in export job)
        self.metadata4tracklog = []  # tracklog:
        self.metadata4data = OrderedDict()  # data:
        self.metadata4display = OrderedDict()  # display:
        self.metadata4access = OrderedDict()  # access:
        self.metadata4masterdata = OrderedDict()  # masterdata:
        self.metadata4fmu = OrderedDict()  # fmu:

        if kwargs.get("dryrun", False):  # developer option, for tests
            logger.info("Dry run mode is active for __init__")
            return

        # strat metadata are used as componenents in some of the other meta keys
        self._get_meta_strat()

        # Get the metadata for some of the general stuff, fully or partly
        # Note that data and display are found later (e.g. in _export_item)
        self._get_meta_masterdata()
        self._get_meta_access()
        self._get_meta_tracklog()
        self._get_meta_fmu()

        logger.info("Create instance of ExportData")

    @staticmethod
    def _check_subfolder(foldername: Optional[str] = None):
        """Check and verify subfolder."""
        if foldername is None:
            return

        if "/" in foldername:
            warnings.warn(
                "The subfolder input contains a path reference '/' which is currently "
                "allowed, but is an antipattern. In future versions only subfolder "
                "names without path references will be allowed. Consider using "
                "the 'forcefolder' key instead if special paths are required.",
                UserWarning,
            )
        else:
            warnings.warn(
                "Exporting to a subfolder is a deviation from the standard "
                "and could have consequences for later dependencies",
                UserWarning,
            )
        return foldername

    def _check_forcefolder(self, foldername: Optional[str] = None):
        """Check and verify forcefolder path, and always return an absolute path.

        In case '/some/path' the path is considered to be absolute
        In case 'some/path' the path is considered to be relative to RUNPATH

        """
        if foldername is None:
            return
        if not isinstance(foldername, str):
            raise ValueError("The forcefolder input must be a string")

        warnings.warn(
            "Using the forcefolder key shall only be done in exceptional cases",
            UserWarning,
        )

        if foldername.startswith("/"):
            # this is a brutal force as it also resets runpath!
            self._runpath = pathlib.Path("/")
            logger.info("The runpath is reset! %s", self._runpath)
            return pathlib.Path(foldername)

        else:
            return self._runpath / foldername

    # ==================================================================================
    # Private attributes that are or may be exposed read-only for other classes

    @property
    def runpath(self):
        """Return runpath which is the relative path to run root folder."""
        return self._runpath

    @property
    def context(self):
        """Return context."""
        return self._context

    @property
    def content(self):
        """Return content."""
        return self._content

    @property
    def config(self):
        """Return config."""
        return self._config

    @property
    def subfolder(self):
        """Return subfolder name."""
        return self._subfolder

    @property
    def forcefolder(self):
        """Return forcefolder name."""
        return self._forcefolder

    @property
    def include_index(self):
        """Return include_index boolean."""
        return self._include_index

    @property
    def vertical_domain(self):
        """Return domain dict."""
        return self._vertical_domain

    @property
    def timedata(self):
        """Return timedata."""
        return self._timedata

    @property
    def is_prediction(self):
        """Return is_prediction boolean."""
        return self._is_prediction

    @property
    def is_observation(self):
        """Return is_observation boolean."""
        return self._is_observation

    @property
    def workflow(self):
        """Return workflow string."""
        return self._workflow

    @property
    def itername(self):
        """Return itername string."""
        return self._itername

    @property
    def realname(self):
        """Return realname string."""
        return self._realname

    @property
    def pwd(self):
        """Return pwd Path object."""
        return self._pwd

    # ==================================================================================
    # Private utility methods

    def _process_pwd_runpath(self, kwargs):
        """Process self._pwd and self._runpath"""

        self._pwd = pathlib.Path().absolute()  # process working directory

        # developer option (for testing): set another pwd
        if kwargs.get("runfolder", None) is not None:
            self._pwd = pathlib.Path(kwargs["runfolder"]).absolute()

        logger.info("Initial RUNPATH is %s", self._runpath)
        logger.info(
            "Inside RMS status (developer setting) is %s",
            kwargs.get("inside_rms", False),
        )
        # Context 1: Running RMS, we are in conventionally in RUNPATH/rms/model
        # Context 2: ERT FORWARD_JOB, running at RUNPATH level
        # Context 3: ERT WORKFLOW_JOB, running somewhere/anywhere else

        if self._runpath and isinstance(self._runpath, (str, pathlib.Path)):
            self._runpath = pathlib.Path(self._runpath).absolute()
            logger.info("The runpath is hard set as %s", self._runpath)
        elif kwargs.get("inside_rms", False) is True and self._runpath is None:
            # Note that runfolder in this case need to be set, pretending to be in the
            # rms/model folder. This is merely a developer setting when running pytest
            # in tmp_path!
            self._runpath = (self._pwd / "../../.").absolute()
            logger.info("Pretend to run from inside RMS")
        elif (
            self._runpath is None
            and "rms" in sys.executable
            and "komodo" not in sys.executable
        ):
            # this is the case when running RMS which happens in runpath/rms/model
            # menaing that actual root runpath is at ../..
            self._runpath = pathlib.Path("../../.").absolute()
            logger.info("Detect 'inside RMS' from 'rms' being in sys.executable")
        elif "RUN_DATAIO_EXAMPLES" in os.environ:  # special; for repo doc examples!
            self._runpath = pathlib.Path("../../.").absolute()
        else:
            self._runpath = self._pwd
            logger.info("Assuming RUNPATH at PWD which is %s", self._pwd)

        logger.info("Current RUNPATH is %s", str(self._runpath))

    # ==================================================================================
    # Private metadata methods which retrieve metadata that are not closely linked to
    # the actual instance to be exported.

    def _config_get(self, args_config):
        """Get the config.

        Config can be provided directly as dictionary in arguments, and will take
        presendence if provided. If not provided, fall-back is to look for pointer
        to a config file in environment variables.

        """

        if args_config is None:
            logger.info("Config is not given as argument")
            config = None
        elif isinstance(args_config, dict):
            logger.info("Config is given as dict in arguments")
            config = args_config
        else:
            logger.info("type of config from args was %s", type(args_config))
            raise TypeError("When config is given as argument, it must be a dictionary")

        if config is None:
            config = self._config_from_environment_variable()

        self._config_validate(config)

        if config is None:
            raise RuntimeError("Could not get config.")

        return config

    def _config_from_environment_variable(self, envvar="FMU_GLOBAL_CONFIG"):
        """Get the config from environment variable.

        This function is only called if config SHALL be fetched from the environment
        variable: Raise if the environment variable is not found.

        Returns: config (dict)
        """

        logger.info("config is still None, try to get from environment variable")

        if envvar in os.environ:
            cfg_path = os.environ[envvar]
            logger.info(
                "Set global config from env variable %s as %s", envvar, cfg_path
            )
        else:
            logger.info("Environment variable %s was not found.", envvar)
            raise ValueError(
                (
                    "No config was received. "
                    "The config must be given explicitly as an input argument, or "
                    "the environment variable %s must point to a valid yaml file.",
                    envvar,
                )
            )

        with open(cfg_path, "r", encoding="utf8") as stream:
            try:
                config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
                raise

        return config

    def _config_validate(self, config):
        """Validate the config.

        Not a full validation. For now, just check that some required
        keys are present in the config and raise if not.

        """

        config_required_keys = ["access", "masterdata", "model"]

        for required_key in config_required_keys:
            if required_key not in config:
                raise ValueError(f"Required key '{required_key}' not found in config.")

    def _get_meta_masterdata(self) -> None:
        """Get metadata from masterdata section in config.

        Having the `masterdata` as hardcoded first level in the config is intentional.
        If that section is missing, or config is None, return with a user warning.

        """
        if self._config is None or "masterdata" not in self._config.keys():
            logger.warning("No masterdata section present")
            self.metadata4masterdata = None
            return

        self.metadata4masterdata = self._config["masterdata"]
        logger.info("Metadata for masterdata is set!")

    def _get_meta_access(self) -> None:
        """Get metadata overall (default) from access section in config.

        Access should be possible to change per object, based on user input.
        This is done through the access_ssdl input argument.

        The "asset" field shall come from the config. This is static information.

        The "ssdl" field can come from the config, or be explicitly given through
        the "access_ssdl" input argument. If the access_ssdl input argument is present,
        its contents shall take presedence.

        """

        logger.info("_get_meta_access()")

        if self._config is None:
            # DISCUSS: Should we allow no config? Or raise when missing?
            logger.debug("No config is given, returning")
            return

        a_cfg = self._config["access"]

        if "asset" not in a_cfg:
            # asset shall be present if config is used
            raise ValueError("The 'access.asset' field not found in the config")

        # initialize and populate with defaults from config
        self.metadata4access = OrderedDict()
        a_meta = self.metadata4access  # shortform

        # if there is a config, the 'asset' tag shall be present
        a_meta["asset"] = a_cfg["asset"]
        logger.debug("meta is now: %s", a_meta)
        logger.info("access.asset is %s", a_meta["asset"])

        # ssdl
        if "ssdl" in a_cfg:
            a_meta["ssdl"] = a_cfg["ssdl"]

        # if input argument, expand or overwrite ssdl tag contents from config
        if not self._case and self._access_ssdl is not None:
            logger.info("access_ssdl has been given: %s", self._access_ssdl)
            a_meta["ssdl"] = {**a_meta["ssdl"], **self._access_ssdl}

        logger.info("access has been set")

    def _get_meta_tracklog(self) -> None:
        """Get metadata for tracklog section."""
        block = OrderedDict()
        block["datetime"] = datetime.datetime.now().isoformat()
        block["user"] = {"id": getpass.getuser()}
        block["event"] = "created"

        self.metadata4tracklog.append(block)
        logger.info("Metadata for tracklog is set")

    def _get_meta_fmu(self) -> None:
        """Get metadata for fmu key."""

        logger.info("Set fmu metadata for model/workflow/...")
        self.metadata4fmu["model"] = self._process_meta_fmu_model()
        if not self._case and self._workflow is not None:
            self._process_meta_fmu_workflow()

        # fmu.element is defaulted to None. Only used in aggregations.
        self.metadata4fmu["element"] = None

        # return now if this is exporting case metadata only
        if self._case:
            return

        self._parse_scratch_folder_structure()

        logger.debug("self._is_fmurun is %s", self._is_fmurun)

        if self._is_fmurun:
            c_meta = self._process_meta_fmu_case()
            self.metadata4fmu["case"] = c_meta
            self._case_uuid = self.metadata4fmu["case"]["uuid"]
            logger.debug("self._case_uuid has been set to %s", self._case_uuid)

        if self._is_fmurun:

            self._get_ert_information()

            i_meta = self._process_meta_fmu_iteration()
            self.metadata4fmu["iteration"] = i_meta

            r_meta = self._process_meta_fmu_realization()
            self.metadata4fmu["realization"] = r_meta

    def _get_ert_information(self):
        """Parse relevant system files from ERT"""

        logger.debug("parsing ERT files")

        # store parameters.txt
        parameters_file = self._iterpath / "parameters.txt"
        if parameters_file.is_file():
            params = _utils.read_parameters_txt(parameters_file)
            nested_params = _utils.nested_parameters_dict(params)
            self._ert["params"] = nested_params
            logger.debug("parameters.txt parsed.")
        logger.debug("parameters.txt was not found")

        # store jobs.json
        jobs_file = self._iterpath / "jobs.json"
        if jobs_file.is_file():
            with open(jobs_file, "r") as stream:
                self._ert["jobs"] = json.load(stream)
            logger.debug("jobs.json parsed.")
        logger.debug("jobs.json was not found")

        logger.debug("ERT files has been parsed.")

    def _process_meta_fmu_workflow(self):
        """Processing the fmu.workflow section.

        self._workflow can be either a str or a dict. Outgoing worklow tag in
        metadata shall be a dict, containing at least a 'reference' key:
        "workflow": {"reference": "MyString"}.

        If self._workflow is provided as a string, the dictionary will be made and the
        string will be used as the value for the 'reference' key.

        If self._workflow is provided as a dict, it shall contain the 'reference' key.
        If self._workflow is provided as a dict, it will be used directly.
        """

        logger.info("Process fmu.workflow...")
        if isinstance(self._workflow, dict):
            logger.info("Workflow input argument is a dictionary")
            if "reference" not in self._workflow.keys():
                raise ValueError("'reference' key not found in workflow dictionary")
            if not isinstance(self._workflow["reference"], str):
                logger.info(
                    "workflow.reference is of type %s",
                    type(self._workflow["reference"]),
                )
                raise ValueError("'reference' value was not a string")
            self.metadata4fmu["workflow"] = self._workflow
        elif isinstance(self._workflow, str):
            logger.info("Workflow input argument is a string")
            self.metadata4fmu["workflow"] = OrderedDict()
            self.metadata4fmu["workflow"]["reference"] = self._workflow
        else:
            logger.info("workflow input argument was not given as dict or str")
            logger.debug("workflow input argument was %s", self._workflow)
            raise ValueError("workflow input argument is not valid")

    # def _process_meta_fmu_context(self):
    #     """Processing the fmu:grid_model section"""

    #     if self._grid_model is None:
    #         logger.info("grid_model was None, assuming it was not passed")
    #         return

    #     meta = self._grid_model

    #     if not isinstance(meta, dict):
    #         logger.error("grid_model: %s", str(meta))
    #         logger.debug("grid_model type was %s", str(type(meta)))
    #         raise ValueError("The grid_model argument must be of type dict")

    #     if "name" not in meta.keys():
    #         logger.error("grid_model: %s", str(meta))
    #         logger.debug("keys in meta: %s", str(meta.keys()))
    #         raise ValueError("grid_model must contain 'name'")

    #     if not isinstance(meta["name"], str):
    #         _gmname = meta["name"]  # shortform
    #         logger.error("grid_model: %s", str(_gmname))
    #         logger.debug("grid_model:name was of type %s", str(type(_gmname)))
    #         raise ValueError("grid_model:name must be a string")

    #     logger.info("grid_model section has been processed")

    #     return meta

    def _process_meta_fmu_model(self):
        """Processing the fmu:model section."""

        # most of the info from global variables section model:
        if self._config is None:
            return

        meta = self._config["model"]

        # the model section in "template" contains root etc. For revision an
        # AUTO name may be used to avoid rapid and error-prone naming
        revision = meta.get("revision", None)
        if revision == "AUTO":
            rev = None
            folders = self._pwd
            for num, _ in enumerate(folders.parents):
                realfoldername = folders.parents[num].name

                # match 20.1.xxx style or r003 style
                if re.match("^[123][0-9]\\.", realfoldername) or re.match(
                    "^[r][0-9][0-9][0-9]", realfoldername
                ):
                    rev = realfoldername
                    break

            meta["revision"] = rev

        logger.info("Got metadata for fmu:model")
        return meta

    def _parse_scratch_folder_structure(self):
        """Detect if this is a ERT run and set the relevant instance variables.

        fmu-dataio will run in different contexts. One of those contexts is when in
        an FMU run, orchestrated by ERT. To detect if we are in such context:

        * See if parameters.txt exists on RUNPATH.
        * Find iter name and realization number from folder names

        e.g.
        /scratch/xxx/user/case/realization-11/iter-3

        The iter folder may have other names, like "pred" which is fully
        supported. Then iter number (id) shall be 0.
        """

        logger.info("Parsing folder structure")

        self._is_fmurun = False

        folders = self._get_folderlist()

        iterfolder = None
        casefolder = None
        userfolder = None

        for num, folder in enumerate(folders):
            if folder and re.match("^realization-.", folder):
                self._is_fmurun = True
                realfolder = folders[num]
                iterfolder = folders[num + 1]
                casefolder = folders[num - 1]
                userfolder = folders[num - 2]

                casepath = pathlib.Path("/".join(folders[0:num]))

                logger.info("Realization folder is %s", realfolder)
                logger.info("Iter folder is %s", iterfolder)
                logger.info("Case folder is %s", casefolder)
                logger.info("User folder is %s", userfolder)
                logger.info("Root path for case is %s", casepath.resolve())

                self._casepath = casepath
                logger.debug("self._casepath has been set to %s", self._casepath)

                # store findings
                self._itername = iterfolder  # name of the folder
                logger.debug("self._itername set to %s", self._itername)

                self._realname = realfolder  # name of the folder
                logger.debug("self._realname set to %s", self._realname)

                # also derive the realization_id (realization number) from the folder
                self._realization_id = int(self._realname.replace("realization-", ""))

                # also derive iteration_id from the folder
                if "iter-" in str(iterfolder):
                    self._iteration_id = int(iterfolder.replace("iter-", ""))
                elif isinstance(iterfolder, str):
                    # any custom name of the iteration, like "pred"
                    self._iteration_id = 0
                else:
                    raise ValueError("Could not derive iteration ID")

                self._iterpath = pathlib.Path(casepath / realfolder / iterfolder)
                logger.debug("self._iterpath set to %s", self._iterpath)

                self._realpath = pathlib.Path(casepath / realfolder)
                logger.debug("self._realpath set to %s", self._realpath)

                return

        logger.info("Could not recognize folder structure, assuming non FMU run.")

    def _process_meta_fmu_iteration(self):
        """Get the iteration metadata"""

        if self._iteration_id is None:
            raise ValueError("self._iteration_id has not been set.")

        if self._case_uuid is None:
            raise ValueError("self._case_uuid has not been set.")

        i_meta = OrderedDict()
        i_meta["id"] = self._iteration_id
        i_meta["uuid"] = _utils.uuid_from_string(
            self._case_uuid + str(self._iteration_id)
        )
        i_meta["name"] = self._itername
        i_meta["runid"] = self._ert["jobs"]["run_id"]
        logger.info("Got metadata for fmu.iteration")
        logger.debug("Iteration meta: \n%s", json.dumps(i_meta, indent=2, default=str))

        return i_meta

    def _process_meta_fmu_realization(self):
        """Get the realization metadata."""

        if self._realname is None:
            raise ValueError("self._realname has not been set.")

        if self._realization_id is None:
            raise ValueError("self._realization_id has not been set.")

        if self._iteration_id is None:
            # in future, allowing for realizations without iterations may be needed.
            raise ValueError("self._iteration_id has not been set.")

        if self._case_uuid is None:
            raise ValueError("self._case_uuid has not been set.")

        r_meta = OrderedDict()

        r_meta["id"] = self._realization_id
        r_meta["name"] = self._realname
        r_meta["uuid"] = _utils.uuid_from_string(
            self._case_uuid + str(self._iteration_id) + str(self._realization_id)
        )

        # Note! export of the "jobs" content is paused. This exports a large amount
        # of data to outgoing metadata, which puts strain on downstream usage. Until
        # clear use case is present, halt the export.

        # r_meta["jobs"] = self._ert["jobs"]
        r_meta["parameters"] = self._ert["params"]

        logger.info("Got metadata for fmu:realization")
        logger.debug("Realiz. meta: \n%s", json.dumps(r_meta, indent=2, default=str))

        return r_meta

    def _process_meta_fmu_case(self):
        """Process fmu.case"""

        if self._casepath is None:
            raise RuntimeError("self._casepath has not been set")

        casemetaroot = self._casepath / "share" / "metadata" / "fmu_case"

        # may be json or yml
        casemetafile = None
        for ext in (".json", ".yml"):
            casemetafile = casemetaroot.with_suffix(ext)
            if casemetafile.is_file():
                break

        logger.debug("casemetafile is %s", casemetafile)
        logger.debug("casemetafile exists: %s", casemetafile.is_file())

        if casemetafile is not None and casemetafile.is_file():
            logger.info("Read existing case metadata from %s", str(casemetafile))

            with open(casemetafile, "r") as stream:
                inmeta = yaml.safe_load(stream)  # will read json also?

            c_meta = inmeta["fmu"]["case"]
        else:
            logger.debug("Case metadata not found, issuing warning")
            # allow case metadata to be missing but issue a warning; consider this
            # as a tmp solution as long as fmu-dataio/sumo is under development!
            warnings.warn(
                "Cannot find the case metadata YAML or JSON file! The run will "
                "continue, but SUMO upload will not be possible! In future versions, "
                "a case metadata file will be a requirement! ",
                FutureWarning,
            )
            # make a fake case name / uuid
            c_meta = {
                "name": "MISSING!",
                "uuid": "not-a-valid-uuid",
            }

        logger.debug("Case meta: \n%s", json.dumps(c_meta, indent=2, default=str))

        return c_meta

    def _get_folderlist(self) -> list:
        """Return a list of pure folder names including current PWD up to system root.

        For example: current is /scratch/xfield/nn/case/realization-33/iter-1
        shall return ['', 'scratch', 'xfield', 'nn', 'case', 'realization-33', 'iter-1']
        """
        current = self._pwd
        flist = [current.name]
        for par in current.parents:
            flist.append(par.name)

        flist.reverse()
        return flist

    def _get_meta_strat(self) -> None:
        """Get metadata from the stratigraphy block in config; used indirectly."""
        if self._config is None:
            logger.warning("Config is missing, not possible to parse stratigraphy")
            self.metadata4strat = None
        elif "stratigraphy" not in self._config:
            logger.warning("Not possible to parse the stratigraphy section")
            self.metadata4strat = None
        else:
            self.metadata4strat = self._config["stratigraphy"]
            logger.info("Metadata for stratigraphy is parsed!")

    # ==================================================================================
    # Public methods
    def export(
        self,
        obj: Any,
        subfolder: Optional[str] = None,
        forcefolder: Optional[str] = None,
        verbosity: Optional[str] = None,
        name: Optional[str] = None,
        unit: Optional[str] = None,
        parent: Optional[str] = None,
        tagname: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        include_index: Optional[bool] = False,
        **kwargs,
    ) -> str:
        """Export data objects of 'known' type to FMU storage solution with metadata.

        A 'known' type is a type which is known to fmu-dataio. Examples of such known
        types are XTGeo objects (e.g. a RegularSurface), a Pandas Dataframe, etc.

        This function will also collect the data spesific class metadata. For "classic"
        files, the metadata will be stored i a YAML file with same name stem as the
        data, but with a . in front and "yml" and suffix, e.g.::

            top_volantis--depth.gri
            .top_volantis--depth.gri.yml

        For formats supporting embedded metadata, other solutions may be used.

        Args:
            obj: XTGeo instance or a Pandas Dataframe instance (more to be supported).
            subfolder: Optional subfolder below standard level to export to.
            verbosity: Verbosity level of logging messages. If not spesified,
                the verbosity level from the instance will be used.
            name: Override any setting in class initialization. The name of the
                object. If not set it is tried to be inferred from
                the xtgeo/pandas/... object. The name is then checked towards the
                stratigraphy list, and name is replaced with official stratigraphic
                name if found in static metadata `stratigraphy`. For example, if
                "TopValysar" is the model name and the actual name
                is "Valysar Top Fm." that latter name will be used.
            unit: Is the unit of the exported item(s), e.g. "m" or "fraction".
            tagname: Override any setting in class initialization. This is a short
                tag description which will be a part of file name and data.tagname.
            parent: Override any setting in class initialization. This key is
                required for datatype GridProperty, and refers to the name of the
                grid geometry.
            description: Override any setting in class initialization. A multiline
                description of the data.
            display_name: Override any setting in class initialization. Set name
                for clients to use when visualizing. Defaults to name if not given.
            include_index: For Pandas table output. If True, then the index column will
                be included. For backward compatibilty, ``index`` also supported.

        Returns:
            String: full path to exported item.
        """
        if kwargs.get("index", False) is True:  # backward compatibility
            include_index = True

        exporter = _ExportItem(
            self,
            obj,
            subfolder=self._check_subfolder(subfolder),
            forcefolder=self._check_forcefolder(forcefolder),
            verbosity=verbosity,
            name=name,
            parent=parent,
            tagname=tagname,
            display_name=display_name,
            description=description,
            unit=unit,
            include_index=include_index,
        )

        # will return the absolute (resolved) path for exported file
        return exporter.save_to_file()

    @deprecation.deprecated(
        deprecated_in="0.5",
        removed_in="1.0",
        current_version=version,
        details="Method to_file() is deprecated. Use export() instead",
    )
    def to_file(self, *args, **kwargs):
        """(Deprecated) Use ``export`` function instead."""
        return self.export(*args, **kwargs)


# ######################################################################################
# InitializeCase
# ######################################################################################


class InitializeCase(ExportData):  # pylint: disable=too-few-public-methods
    """Instantate ExportData object.

    Args:
        config: A configuration dictionary. In the standard case this is read
            from FMU global variables (via fmuconfig). The dictionary must contain
            some predefined main level keys. If config is None and the env variable
            FMU_GLOBAL_CONFIG pointing to file is provided, then it will attempt to
            parse that file.
        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO".
    """

    def __init__(  # pylint: disable=super-init-not-called
        self,
        config: Optional[dict] = None,
        verbosity: Optional[str] = "CRITICAL",
        **kwargs,
    ) -> None:
        self._verbosity = verbosity
        logger.setLevel(level=self._verbosity)

        self._config = self._config_get(config)

        self._case = True

        self._pwd = pathlib.Path().absolute()
        logger.info("Create instance of InitializeCase")

        if kwargs.get("runfolder", None) is not None:
            self._pwd = pathlib.Path(kwargs["runfolder"]).absolute()

        # define chunks of metadata for primary first order categories
        # (except class which is set directly later)
        self.metadata4strat = None
        self.metadata4dollars = DOLLARS  # schema, version, source
        self.metadata4file = OrderedDict()  # file (to be populated in export job)
        self.metadata4tracklog = []  # tracklog:
        self.metadata4data = OrderedDict()  # data:
        self.metadata4display = OrderedDict()  # display:
        self.metadata4access = OrderedDict()  # access:
        self.metadata4masterdata = OrderedDict()  # masterdata:
        self.metadata4fmu = OrderedDict()  # fmu:

        if kwargs.get("dryrun", False):
            return

        # strat metadata are used as componenents in some of the other meta keys
        super()._get_meta_strat()

        # Get the metadata for some of the general stuff, fully or partly
        # Note that data are found later (e.g. in _export_item)
        super()._get_meta_masterdata()
        super()._get_meta_access()
        super()._get_meta_tracklog()
        super()._get_meta_fmu()

    # ==================================================================================
    # Store case data.

    def _store_case_metadata(self, casefolder, c_meta):
        if not c_meta:
            return

        logger.info("Storing case metadata...")
        case_meta_exists = False

        share_caseroot = pathlib.Path(casefolder)

        try:
            share_caseroot.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            logger.warning("The metadata folder root exists already: ")
        else:
            logger.info("The metadata folder root is created: %s", str(share_caseroot))

        metafile = share_caseroot / "fmu_case.yml"

        logger.info("Case metadata file: %s", str(metafile))

        existing_metadata = {}

        if metafile.is_file():
            logger.debug("Case metadata file already exists. So parsing it.")
            with open(metafile, "r") as stream:
                existing_metadata = yaml.safe_load(stream)

        if existing_metadata:
            logger.debug("Reusing fmu.case.uuid")
            fmu_case_uuid = existing_metadata["fmu"]["case"]["uuid"]
        else:
            logger.debug("Creating fresh fmu.case.uuid")
            fmu_case_uuid = str(uuid.uuid4())

        logger.debug("fmu.case.uuid is %s", fmu_case_uuid)
        c_meta["uuid"] = fmu_case_uuid

        meta = self.metadata4dollars.copy()
        meta["class"] = "case"

        meta["fmu"] = OrderedDict()
        meta["fmu"]["case"] = c_meta
        meta["fmu"]["model"] = self.metadata4fmu["model"]

        # Should not be possible to initialize a case without
        # the access.asset field be present.
        # Outgoing case metadata should contain access.asset only
        if not self.metadata4access:
            logger.debug("self.metadata4access is %s", str(self.metadata4access))
            logger.error("Cannot proceed without access information.")
            raise ValueError("Access information missing.")
        if "asset" not in self.metadata4access.keys():

            logger.error("'access' key not found under 'asset'")
        meta["access"] = {"asset": self.metadata4access["asset"]}

        meta["masterdata"] = self.metadata4masterdata
        meta["tracklog"] = list()

        track = OrderedDict()

        track["datetime"] = datetime.datetime.now().isoformat()
        track["event"] = "created"
        track["user"] = OrderedDict()
        track["user"]["id"] = getpass.getuser()
        meta["tracklog"].append(track)

        # in case the file is deleted but the folder exists
        if not metafile.is_file():
            logger.info("Case metafile is %s", str(metafile))
            case_meta_exists = False

        if not case_meta_exists:
            # collect needed metadata and save to disk
            logger.info("Create case metadata as %s", str(metafile))
            _utils.export_metadata_file(
                metafile, meta, verbosity=self._verbosity, savefmt=self.meta_format
            )

        else:
            logger.warning(
                "Metadata case file already exists for the case!: %s", metafile
            )

        return metafile

    @staticmethod
    def _establish_fmu_case_metadata(
        casename="unknown",
        caseuser="nn",
        restart_from=None,
        description=None,
    ):
        """Establish the fmu.case card."""
        c_meta = OrderedDict()

        # iterfolder something like /scratch/xxx/user/casename/iter-0

        c_meta["name"] = casename
        # uuid is inserted at later stage
        c_meta["user"] = OrderedDict()
        c_meta["user"]["id"] = caseuser
        if restart_from is not None:
            c_meta["restart_from"] = restart_from
        timeid = datetime.datetime.now().isoformat()
        c_meta["description"] = [f"Generated by {getpass.getuser()} at {timeid}"]
        if description:
            c_meta["description"].append(description)

        return c_meta

    def export(  # pylint: disable=arguments-differ
        self,
        rootfolder="/tmp/",
        casename="unknown",
        caseuser="nn",
        restart_from=None,
        description=None,
    ):
        """Export the case metadata to file, e.g. when in an ERT run.

        This will be the configuration file and output the data necessary to
        generate a general case ID, typically done as a hook workflow in ERT
        or similar.

        Args:
            rootfolder: The folder root of case, e.g. /scratch/fmu/user/mycase
            casename: Name of case (run), e.g. 'mycase'
            caseuser: The username fro the case, e.g. the <USER> in ERT
            restart_from: The uid of iteration from whci to run from
            description: A free-form description for case

        This will make an communication point to storage in cloud::

            case = InitializeCase(config=configdict)
            case.export(rootfolder=somefolder, caseuser=some_user)
        """

        c_meta = self._establish_fmu_case_metadata(
            caseuser=caseuser,
            casename=casename,
            restart_from=restart_from,
            description=description,
        )

        casefolder = pathlib.Path(rootfolder) / pathlib.Path(self.case_folder)

        logger.info("C_META is:\n%s", json.dumps(c_meta, indent=2))
        logger.info("case_folder:%s", casefolder)

        # write to file and return the path to stored metadata
        return self._store_case_metadata(casefolder, c_meta)

    @deprecation.deprecated(
        deprecated_in="0.5",
        removed_in="1.0",
        current_version=version,
        details="Method to_file() is deprecated. Use export() instead",
    )
    def to_file(self, *args, **kwargs):
        """(Deprecated) Use ``export`` function instead."""
        self.export(*args, **kwargs)
