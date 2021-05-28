"""Module for DataIO class.

The metadata spec is presented in
https://github.com/equinor/fmu-metadata/blob/dev/definitions/0.7.*/

The processing is based on handling first level keys which are

-- scalar SPECIALS (previous marked with $ prefix) --
schema      |      hard set in code
version     |     "dollars", source fmuconfig
source      |

class        - determined by datatype, inferred

-- nested --
file         - file paths and checksums (change) still a discussion where to be
tracklog     - data events, source = ?
data         - about the data (see class). inferred from data + fmuconfig
display      - Deduced mostly from fmuconfig
fmu          - Deduced from fmuconfig (and ERT run?)
access       - Static, infer from fmuconfig
masterdata   - Static, infer from fmuconfig

"""
from typing import Optional, Union, Any
import pathlib
import re
import uuid
from collections import OrderedDict

import datetime
import getpass

import logging
import json
import yaml

from ._export_item import _ExportItem
from . import _utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

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
    """Class for exporting data with rich metadata in FMU."""

    surface_fformat = "hdf"
    table_fformat = "csv"
    polygons_fformat = "csv"
    grid_fformat = "hdf"
    export_root = "../../share/results"
    case_folder = "share/metadata"  # e.g. /some_rootpath/case/metadata
    createfolder = True
    meta_format = "yaml"

    def __init__(
        self,
        name: Optional[str] = None,
        relation: Optional[dict] = None,
        config: Optional[dict] = None,
        content: Optional[Union[str, dict]] = None,
        unit: Optional[str] = None,
        tagname: Optional[str] = None,
        vertical_domain: Optional[dict] = None,
        timedata: Optional[list] = None,
        is_prediction: Optional[bool] = True,
        is_observation: Optional[bool] = False,
        workflow: Optional[str] = None,
        access_ssdl: Optional[dict] = None,
        runfolder: Optional[str] = None,
        verbosity: Optional[str] = "CRITICAL",
    ) -> None:
        """Instantate ExportData object.

        Args:
            name: The name of the object. If not set it is tried to be inferred from
                the xtgeo object. The name is then checked towards the stratigraphy
                list, and name is replaced with official stratigraphic name if found.
                For example, if "TopValysar" is the model name and the actual name
                is "Valysar Top Fm." that latter name will be used.
            relation: The relation of the object with respect to itself and/or
                other stratigraphic units. The default is None, but for e.g. seismic
                attributes this can be important. The input is a dictionary with
                the following fields: to-be...
            config: A configuation dictionary. In the standard case this is read
                from FMU global vaiables (via fmuconfig). The dictionary must contain
                some predefined main level keys.
            content: Is a string or a dictionary with one key. Example is "depth" or
                {"fluid_contact": {"xxx": "yyy", "zzz": "uuu"}}
            unit: Is the unit of the exported item(s), e.g. "m" or "fraction".
            tagname: This is a short tag description which be be a part of file name
            vertical_domain: This is dictionary with a key and a reference e.g.
                {"depth": "msl"} which is default (if None is input)
            timedata: If given, a list of lists with dates, .e.g.
                [[20200101, "firsttime"], [20180101, "secondtime"]] or just [[20210101]]
            is_prediction: True (default) of model prediction data
            is_observation: Default is False.
            workflow: Short tag desciption of workflow (as description)
            access_ssdl: A dictionary that will overwrite the default ssdl
                settings read from the config. Example:
                {"access_level": "restricted", "rep_include": False}
            runfolder: Set toplevel of runfolder, where default is current PWD
            verbosity: Is logging/message level for this module. Input as
                in standard python logging; e.g. "WARNING", "INFO".

        """

        self._name = name
        self._relation = relation
        self._config = config
        self._content = content
        self._unit = unit
        self._tagname = tagname
        self._timedata = timedata
        self._vertical_domain = (
            {"depth": "msl"} if vertical_domain is None else vertical_domain
        )
        self._is_prediction = is_prediction
        self._is_observation = is_observation
        self._workflow = workflow
        self._access_ssdl = access_ssdl
        self._verbosity = verbosity

        # keep track if case
        self._case = False

        # store iter and realization folder names (when running ERT)
        self._iterfolder = None
        self._realfolder = None

        logger.setLevel(level=self._verbosity)
        self._pwd = pathlib.Path().absolute()
        logger.info("Create instance of ExportData")
        if runfolder:
            self._pwd = pathlib.Path(runfolder).absolute()

        # define chunks of metadata for primary first order categories
        # (except class which is set directly later)
        self._meta_strat = None
        self._meta_dollars = DOLLARS  # schema, version, source
        self._meta_file = OrderedDict()  # file (to be populated in export job)
        self._meta_tracklog = []  # tracklog:
        self._meta_data = OrderedDict()  # data:
        self._meta_display = OrderedDict()  # display:
        self._meta_access = OrderedDict()  # access:
        self._meta_masterdata = OrderedDict()  # masterdata:
        self._meta_fmu = OrderedDict()  # fmu:

        # strat metadata are used as componenents in some of the other meta keys
        self._get_meta_strat()

        # Get the metadata for some of the general stuff, fully or partly
        # Note that data are found later (e.g. in _export_item)
        self._get_meta_masterdata()
        self._get_meta_access()
        self._get_meta_tracklog()
        self._get_meta_fmu()

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
            self._meta_masterdata = None
            return

        self._meta_masterdata = self._config["masterdata"]
        logger.info("Metadata for masterdata is set!")

    def _get_meta_access(self) -> None:
        """Get metadata overall (default) from access section in config."""
        # note that access should be possible to change per object
        if self._config is None or "access" not in self._config.keys():
            logger.warning("No access section present")
            self._meta_access = None
            return

        self._meta_access = self._config["access"]
        logger.info("Metadata for access is set!")

    def _get_meta_tracklog(self) -> None:
        """Get metadata for tracklog section."""
        block = OrderedDict()
        block["datetime"] = datetime.datetime.now().isoformat()
        block["user"] = {"id": getpass.getuser()}
        block["event"] = "created"

        self._meta_tracklog.append(block)
        logger.info("Metadata for tracklog is set")

    def _get_meta_fmu(self) -> None:
        """Get metadata for fmu key.

        The fmu block consist of these subkeys:
            model:
            workflow:
            element:  # if aggadation
            realization OR aggradation:
            iteration:
            case:
        """
        logger.info("Set fmu metadata for model/workflow/...")
        self._meta_fmu["model"] = self._process_meta_fmu_model()
        if not self._case and self._workflow is not None:
            logger.info("Set fmu.workflow...")
            self._meta_fmu["workflow"] = OrderedDict()
            self._meta_fmu["workflow"]["refence"] = self._workflow

        self._meta_fmu["element"] = None

        if self._case:
            return

        c_meta, i_meta, r_meta = self._process_meta_fmu_realization_iteration()
        self._meta_fmu["case"] = c_meta
        self._meta_fmu["iteration"] = i_meta
        self._meta_fmu["realization"] = r_meta
        logger.info("Metadata for realization/iteration/case is parsed!")

        if r_meta is None:
            logger.info(
                "Note that metadata for realization is None, "
                "so this is interpreted as not an ERT run!"
            )

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
            for num in range(len(folders.parents)):
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
        """Detect if this is a realization run.

        To detect if a realization run:
        * See of parameters.txt json at iter level
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

        folders = self._pwd
        logger.info("Folder to evaluate: %s", self._pwd)
        therealization = None
        ertjob = OrderedDict()

        iterfolder = None
        casefolder = None
        userfolder = None

        for num in range(len(folders.parents)):
            foldername = folders.parents[num].name
            if re.match("^realization-.", foldername):
                is_fmurun = True
                realfolder = pathlib.Path(self._pwd).resolve().parents[num]
                iterfolder = pathlib.Path(self._pwd).resolve().parents[num - 1]
                casefolder = pathlib.Path(self._pwd).resolve().parents[num + 1]
                userfolder = pathlib.Path(self._pwd).resolve().parents[num + 2]

                logger.info("Realization folder is %s", realfolder.name)
                logger.info("Iter folder is %s", iterfolder.name)
                logger.info("Case folder is %s", casefolder.name)
                logger.info("User folder is %s", userfolder.name)

                self._iterfolder = iterfolder.name
                self._realfolder = realfolder.name

                therealization = realfolder.name.replace("realization-", "")

                # store parameters.txt and jobs.json
                parameters_file = iterfolder / "parameters.txt"
                if parameters_file.is_file():
                    params = _utils.read_parameters_txt(parameters_file)
                    ertjob["params"] = params

                jobs_file = iterfolder / "jobs.json"
                if jobs_file.is_file():
                    with open(jobs_file, "r") as stream:
                        ertjob["jobs"] = json.load(stream)

                break

        if not is_fmurun:
            return None, None, None

        # ------------------------------------------------------------------------------
        # get the case metadata which shall be established already
        casemetaroot = casefolder / "share" / "metadata" / "fmu_case"
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
        i_meta["uuid"] = _utils.uuid_from_string(c_meta["uuid"] + iterfolder.name)
        i_meta["id"] = 0
        if "iter-" in iterfolder.name:
            i_meta["id"] = int(iterfolder.name.replace("iter-", ""))
        i_meta["name"] = iterfolder.name
        i_meta["runid"] = runid

        # ------------------------------------------------------------------------------
        # get the realization metadata
        r_meta = OrderedDict()
        r_meta["id"] = int(therealization)
        r_meta["name"] = realfolder.name
        r_meta["uuid"] = _utils.uuid_from_string(
            c_meta["uuid"] + str(i_meta["id"]) + str(r_meta["id"])
        )
        r_meta["jobs"] = ertjob["jobs"]
        r_meta["parameters"] = ertjob["params"]

        logger.info("Got metadata for fmu:realization")
        logger.debug("Case meta: \n%s", json.dumps(c_meta, indent=2, default=str))
        logger.debug("Iteration meta: \n%s", json.dumps(i_meta, indent=2, default=str))
        logger.debug("Realiz. meta: \n%s", json.dumps(r_meta, indent=2, default=str))

        return c_meta, i_meta, r_meta

    def _get_meta_strat(self) -> None:
        """Get metadata from the stratigraphy block in config; used indirectly."""

        if self._config is None:
            logger.warning("Config is missing, not possible to parse stratigraphy")
            self._meta_strat = None
        elif "stratigraphy" not in self._config:
            logger.warning("Not possible to parse the stratigraphy section")
            self._meta_strat = None
        else:
            self._meta_strat = self._config["stratigraphy"]
            logger.info("Metadata for stratigraphy is parsed!")

    # ==================================================================================
    # Public methods

    def to_file(self, obj: Any, verbosity: Optional[str] = None):
        """Export a XTGeo data object to FMU file with rich metadata.

        Since xtgeo and Python  will know the datatype from the object, a general
        function like this should work.

        This function will also collect the data spesific class metadata. For "classic"
        files, the metadata will be stored i a YAML file with same name stem as the
        data, but with a . in front and "yml" and suffix, e.g.::

            top_volantis--depth.gri
            .top_volantis--depth.yml

        For HDF files the metadata will be stored on the _freeform_ block.

        Args:
            obj: XTGeo instance or a pandas instance (more to be supported).
            verbosity: Verbosity level of logging messages. If not spesified,
                use the verbosity level from the instance.

        """

        logger.info("Export to file...")
        exporter = _ExportItem(self, obj, verbosity=verbosity)
        exporter.save_to_file()


# ######################################################################################
# InitializeCase
# ######################################################################################
class InitializeCase(ExportData):  # pylint: disable=too-few-public-methods
    def __init__(  # pylint: disable=super-init-not-called
        self,
        config: Optional[dict] = None,
        verbosity: Optional[str] = "CRITICAL",
        runfolder: Optional[str] = None,
    ) -> None:
        """Instantate ExportData object.

        Args:
            config: A configuation dictionary. In the standard case this is read
                from FMU global vaiables (via fmuconfig). The dictionary must contain
                some predefined main level keys.
            verbosity: Is logging/message level for this module. Input as
                in standard python logging; e.g. "WARNING", "INFO".
        """

        self._config = config
        self._verbosity = verbosity

        self._case = True

        logger.setLevel(level=self._verbosity)
        self._pwd = pathlib.Path().absolute()
        logger.info("Create instance of InitializeCase")

        if runfolder:
            self._pwd = pathlib.Path(runfolder).absolute()

        # define chunks of metadata for primary first order categories
        # (except class which is set directly later)
        self._meta_strat = None
        self._meta_dollars = DOLLARS  # schema, version, source
        self._meta_file = OrderedDict()  # file (to be populated in export job)
        self._meta_tracklog = []  # tracklog:
        self._meta_data = OrderedDict()  # data:
        self._meta_display = OrderedDict()  # display:
        self._meta_access = OrderedDict()  # access:
        self._meta_masterdata = OrderedDict()  # masterdata:
        self._meta_fmu = OrderedDict()  # fmu:

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

        existing_metadata = None

        if metafile.is_file():
            logger.debug("Case metadata file already exists. So parsing it.")
            with open(metafile, "r") as stream:
                existing_metadata = yaml.safe_load(stream)

        if existing_metadata is not None:
            logger.debug("Reusing fmu.case.uuid")
            fmu_case_uuid = existing_metadata["fmu"]["case"]["uuid"]
        else:
            logger.debug("Creating fresh fmu.case.uuid")
            fmu_case_uuid = str(uuid.uuid4())

        logger.debug("fmu.case.uuid is %s", fmu_case_uuid)
        c_meta["uuid"] = fmu_case_uuid

        meta = self._meta_dollars.copy()
        meta["class"] = "case"

        meta["fmu"] = OrderedDict()
        meta["fmu"]["case"] = c_meta
        meta["fmu"]["model"] = self._meta_fmu["model"]

        # Should not be possible to initialize a case without
        # the access.asset field be present.
        # Outgoing case metadata should contain access.asset only
        if not self._meta_access:
            logger.debug("self._meta_access is %s", str(self._meta_access))
            logger.error("Cannot proceed without access information.")
            raise ValueError("Access information missing.")
        if "asset" not in self._meta_access.keys():

            logger.error("the access field in the metadata was missing the asset field")
        meta["access"] = {"asset": self._meta_access["asset"]}

        meta["masterdata"] = self._meta_masterdata
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

    def to_file(  # pylint: disable=arguments-differ
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
            case.to_file(rootfolder=somefolder, caseuser=some_user)
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
