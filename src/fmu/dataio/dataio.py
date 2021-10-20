"""Module for DataIO class.

The metadata spec is presented in
https://github.com/equinor/fmu-metadata/

The processing is based on handling first level keys which are

* Scalar special::

    $schema      |
    version      |     hard set in code
    source       |

* ``class``        - determined by datatype, inferred

* Nested attributes::

    file         - file paths and checksums (change) still a discussion where to be
    tracklog     - data events, source = ?
    data         - about the data (see class). Inferred from data + fmuconfig
    display      - Deduced mostly from fmuconfig (TODO: issue on wait)
    fmu          - Deduced from fmuconfig (and ERT run?)
    access       - Static, infer from fmuconfig
    masterdata   - Static, infer from fmuconfig

"""
import datetime
import getpass
import json
import logging
import pathlib
import re
import sys
import uuid
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
            some predefined main level keys to work with fmu-dataio.
        content: Is a string or a dictionary with one key. Example is "depth" or
            {"fluid_contact": {"xxx": "yyy", "zzz": "uuu"}}
        subfolder: It is possible to set one level of subfolders for file output.
        include_index: This applies to Pandas (table) data only, and if True then the
            index column will be exported.
        vertical_domain: This is dictionary with a key and a reference e.g.
            {"depth": "msl"} which is default (if None is input)
        timedata: If given, a list of lists with dates, .e.g.
            [[20200101, "monitor"], [20180101, "base"]] or just [[20210101]]
        is_prediction: True (default) of model prediction data
        is_observation: Default is False.
        workflow: Short tag desciption of workflow (as description)

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
        access_ssdl: A dictionary that will overwrite the default ssdl
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
    polygons_fformat = "csv"
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
        timedata: Optional[list] = None,
        include_index: Optional[bool] = False,
        vertical_domain: Optional[dict] = None,
        workflow: Optional[str] = None,
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
        self._runpath = runpath
        self._access_ssdl = access_ssdl
        self._config = config
        self._content = content
        self._context = context
        self._is_prediction = is_prediction
        self._is_observation = is_observation
        self._timedata = timedata
        self._vertical_domain = (
            {"depth": "msl"} if vertical_domain is None else vertical_domain
        )
        self._subfolder = subfolder
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

        self._verbosity = verbosity

        # keep track of case
        self._case = False

        # store iter and realization folder names (when running ERT)
        self._iterfolder = None
        self._realfolder = None

        logger.setLevel(level=self._verbosity)
        self._pwd = pathlib.Path().absolute()  # process working directory

        # developer option (for testing): set another pwd
        if kwargs.get("runfolder", None) is not None:
            self._pwd = pathlib.Path(kwargs["runfolder"]).absolute()

        logger.info("Initial RUNPATH is %s", self._runpath)
        logger.info(
            "Inside RMS status (developer setting) is %s",
            kwargs.get("inside_rms", False),
        )
        # When running RMS, we are in conventionally in RUNPATH/rms/model, while
        # in other settings, we run right at RUNPATH level (e.g. ERT jobs)
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
        else:
            self._runpath = self._pwd
            logger.info("Assuming RUNPATH at PWD which is %s", self._pwd)

        logger.info("Current RUNPATH is %s", str(self._runpath))

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
    def iterfolder(self):
        """Return iterfolder string."""
        return self._iterfolder

    @property
    def realfolder(self):
        """Return realfolder string."""
        return self._realfolder

    @property
    def pwd(self):
        """Return pwd Path object."""
        return self._pwd

    # ==================================================================================
    # Private metadata methods which retrieve metadata that are not closely linked to
    # the actual instance to be exported.

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
        """Get metadata overall (default) from access section in config."""
        # note that access should be possible to change per object
        if self._config is None or "access" not in self._config.keys():
            logger.warning("No access section present")
            self.metadata4access = None
            return

        self.metadata4access = self._config["access"]
        logger.info("Metadata for access is set!")

    def _get_meta_tracklog(self) -> None:
        """Get metadata for tracklog section."""
        block = OrderedDict()
        block["datetime"] = datetime.datetime.now().isoformat()
        block["user"] = {"id": getpass.getuser()}
        block["event"] = "created"

        self.metadata4tracklog.append(block)
        logger.info("Metadata for tracklog is set")

    def _get_meta_fmu(self) -> None:
        """Get metadata for fmu key.

        The fmu block consist of these subkeys:
            model:
            case:
            workflow:
            element:  # if aggadation
            realization OR aggradation:
            iteration:
        """
        logger.info("Set fmu metadata for model/workflow/...")
        self.metadata4fmu["model"] = self._process_meta_fmu_model()
        if not self._case and self._workflow is not None:
            logger.info("Set fmu.workflow...")
            self.metadata4fmu["workflow"] = OrderedDict()
            self.metadata4fmu["workflow"]["refence"] = self._workflow

        self.metadata4fmu["element"] = None

        if self._case:
            return

        c_meta, i_meta, r_meta = self._process_meta_fmu_realization_iteration()
        self.metadata4fmu["case"] = c_meta
        self.metadata4fmu["iteration"] = i_meta
        self.metadata4fmu["realization"] = r_meta
        logger.info("Metadata for realization/iteration/case is parsed!")

        if r_meta is None:
            logger.info(
                "Note that metadata for realization is None, "
                "so this is interpreted as not an ERT run!"
            )

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

    def _process_meta_fmu_realization_iteration(self):
        """Detect if this is a ERT run and in case provide real, iter, case info.

        To detect if a realization run:
        * See if parameters.txt json at iter level
        * find iter name and realization number from folder names

        e.g.
        /scratch/xxx/user/case/realization-11/iter-3

        The iter folder may have other names, like "pred" which is fully
        supported. Then iter number (id) shall be 0.

        Will also parse the fmu.case metadata block from file which is stored
        higher up and generated in-advance.
        """
        logger.info("Process metadata for realization and iteration")
        is_fmurun = False

        folders = self._get_folderlist()

        therealization = None
        ertjob = OrderedDict()

        iterfolder = None
        casefolder = None
        userfolder = None

        for num, folder in enumerate(folders):
            if folder and re.match("^realization-.", folder):
                is_fmurun = True
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

                self._iterfolder = pathlib.Path(casepath / realfolder / iterfolder)
                self._realfolder = pathlib.Path(casepath / realfolder)

                therealization = realfolder.replace("realization-", "")

                # store parameters.txt
                parameters_file = self._iterfolder / "parameters.txt"
                if parameters_file.is_file():
                    params = _utils.read_parameters_txt(parameters_file)
                    nested_params = _utils.nested_parameters_dict(params)
                    ertjob["params"] = nested_params

                # store jobs.json
                jobs_file = self._iterfolder / "jobs.json"
                if jobs_file.is_file():
                    with open(jobs_file, "r") as stream:
                        ertjob["jobs"] = json.load(stream)

                break

        if not is_fmurun:
            return None, None, None

        # ------------------------------------------------------------------------------
        # get the case metadata which shall be established already
        casemetaroot = casepath / "share" / "metadata" / "fmu_case"

        # may be json or yml
        casemetafile = None
        for ext in (".json", ".yml"):
            casemetafile = casemetaroot.with_suffix(ext)
            if casemetafile.is_file():
                break
        if casemetafile is None:
            raise RuntimeError(f"Cannot find any case metafile! {casemetafile}.*")

        logger.info("Read existing case metadata from %s", str(casemetafile))

        with open(casemetafile, "r") as stream:
            inmeta = yaml.safe_load(stream)  # will read json also?

        c_meta = inmeta["fmu"]["case"]

        # ------------------------------------------------------------------------------
        # get the iteration metadata
        runid = ertjob["jobs"]["run_id"].replace(":", "_")
        i_meta = OrderedDict()
        i_meta["uuid"] = _utils.uuid_from_string(c_meta["uuid"] + iterfolder)
        i_meta["id"] = 0
        if "iter-" in iterfolder:
            i_meta["id"] = int(iterfolder.replace("iter-", ""))
        i_meta["name"] = iterfolder
        i_meta["runid"] = runid

        # ------------------------------------------------------------------------------
        # get the realization metadata
        r_meta = OrderedDict()
        r_meta["id"] = int(therealization)
        r_meta["name"] = realfolder
        r_meta["uuid"] = _utils.uuid_from_string(
            c_meta["uuid"] + str(i_meta["id"]) + str(r_meta["id"])
        )

        # Note! export of the "jobs" content is paused. This exports a large amount
        # of data to outgoing metadata, which puts strain on downstream usage. Until
        # clear use case is present, halt the export.

        # r_meta["jobs"] = ertjob["jobs"]
        r_meta["parameters"] = ertjob["params"]

        logger.info("Got metadata for fmu:realization")
        logger.debug("Case meta: \n%s", json.dumps(c_meta, indent=2, default=str))
        logger.debug("Iteration meta: \n%s", json.dumps(i_meta, indent=2, default=str))
        logger.debug("Realiz. meta: \n%s", json.dumps(r_meta, indent=2, default=str))

        return c_meta, i_meta, r_meta

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
        """Export a 'known' data object to FMU storage solution with rich metadata.

        The 'known' datatype is a XTGeo object (e.g. a RegularSurface), a Pandas
        Dataframe or (in future) a Arrow object.

        This function will also collect the data spesific class metadata. For "classic"
        files, the metadata will be stored i a YAML file with same name stem as the
        data, but with a . in front and "yml" and suffix, e.g.::

            top_volantis--depth.gri
            .top_volantis--depth.gri.yml

        For HDF files the metadata may be stored on the _freeform_ block (yet to be
        resolved)).

        Args:
            obj: XTGeo instance or a Pandas Dataframe instance (more to be supported).
            subfolder: Optional subfolder below standard level to export to.
            verbosity: Verbosity level of logging messages. If not spesified,
                the verbosity level from the instance will be used.
            name: Override eventual setting in class initialization. The name of the
                object. If not set it is tried to be inferred from
                the xtgeo/pandas/... object. The name is then checked towards the
                stratigraphy list, and name is replaced with official stratigraphic
                name if found in static metadata `stratigraphy`. For example, if
                "TopValysar" is the model name and the actual name
                is "Valysar Top Fm." that latter name will be used.
            unit: Is the unit of the exported item(s), e.g. "m" or "fraction".
            tagname: Override eventual setting in class initialization. This is a short
                tag description which be be a part of file name.
            parent: Override eventual setting in class initialization. This key is
                required for datatype GridProperty, and refers to the name of the
                grid geometry.
            description: Override eventual setting in class initialization. A multiline
                description of the data.
            display_name: Override eventual setting in class initialization. Set name
                for clients to use when visualizing. Defaults to name if not given.
            include_index: For Pandas table output. If True, then the index column will
                be included. For backward compatibilty, ``ìndex`` also supported.

        Returns:
            String: full path to exported item.
        """
        if kwargs.get("index", False) is True:  # backward compatibility
            include_index = True

        exporter = _ExportItem(
            self,
            obj,
            subfolder=subfolder,
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
        details="Method to_file() is deprecated. use export() instead",
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
        config: A configuation dictionary. In the standard case this is read
            from FMU global vaiables (via fmuconfig). The dictionary must contain
            some predefined main level keys.
        verbosity: Is logging/message level for this module. Input as
            in standard python logging; e.g. "WARNING", "INFO".
    """

    def __init__(  # pylint: disable=super-init-not-called
        self,
        config: Optional[dict] = None,
        verbosity: Optional[str] = "CRITICAL",
        **kwargs,
    ) -> None:

        self._config = config
        self._verbosity = verbosity

        self._case = True

        logger.setLevel(level=self._verbosity)
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

            logger.error("the access field in the metadata was missing the asset field")
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
        """Export the case metadata to file, e.g. when ERT run.

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

        # write to file
        self._store_case_metadata(casefolder, c_meta)

    @deprecation.deprecated(
        deprecated_in="0.5",
        removed_in="1.0",
        current_version=version,
        details="Method to_file() is deprecated. use export() instead",
    )
    def to_file(self, *args, **kwargs):
        """(Deprecated) Use ``export`` function instead."""
        self.export(*args, **kwargs)
