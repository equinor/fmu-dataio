"""Module for DataIO class.

The metadata spec is presented in
https://github.com/equinor/fmu-metadata/blob/dev/definitions/0.7.0/

The processing is based on handling first level keys which are:

-- scalar --
$schema      |
$version     | "dollars", source fmuconfig
$source      |

class        - determined by datatype, inferred

-- nested --
events       - data events, source = ?
data         - about the data (see class). inferred from data + fmuconfig
display      - Deduced mostly from fmuconfig
fmu          - Deduced from fmuconfig (and ERT run?)
access       - Static, infer from fmuconfig
masterdata   - Static, infer from fmuconfig

"""
from typing import Union, Optional, Any
import pathlib
import re
import hashlib
from copy import deepcopy
from collections import OrderedDict
from time import sleep

import datetime
import getpass

import warnings
import logging
import json
import yaml

import xtgeo

from . import _surface_io
from . import _grid_io
from . import _utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


class ExportData:
    """Class for exporting data with rich metadata in FMU."""

    surface_fformat = "hdf"
    grid_fformat = "hdf"
    export_root = "../../share/results"

    def __init__(
        self,
        project: Optional[Any] = None,
        config: Optional[dict] = None,
        schema: Optional[str] = "0.6.0",
        fmustandard: Optional[str] = "1",
        createfolder: Optional[bool] = True,
        verbosity: Optional[str] = "CRITICAL",
        description: Optional[str] = None,
        content: Optional[str] = "depth",
        details: Optional[dict] = None,
    ) -> None:
        """Instantate ExportData object."""
        logger.info("Create instance of ExportData")

        self._project = project
        self._config = deepcopy(config)
        self._schema = schema
        self._fmustandard = fmustandard
        self._createfolder = createfolder
        self._content = content
        self._description = description
        self._verbosity = verbosity
        self._details = details

        logger.setLevel(level=self._verbosity)
        self._pwd = pathlib.Path().absolute()

        # define metadata for primary first order categories (except class which is set
        # directly later)
        self._meta_strat = None
        self._meta_dollars = OrderedDict()  # $version etc
        self._meta_file = OrderedDict()  # file (to be populated in export job)
        self._meta_tracklog = []  # tracklog:
        self._meta_data = OrderedDict()  # data:
        self._meta_display = OrderedDict()  # display:
        self._meta_access = OrderedDict()  # access:
        self._meta_masterdata = OrderedDict()  # masterdata:
        self._meta_fmu = OrderedDict()  # fmu:

        # aux metadata are used as componenents in some of the other meta keys
        self._get_meta_strat()

        # Get the metadata for some of the general stuff, fully or partly
        # Note that data and display are found later (e.g. in _surface_io)
        self._get_meta_dollars()
        self._get_meta_masterdata()
        self._get_meta_access()
        self._get_meta_tracklog()
        self._get_meta_fmu()

        self._store_ensemble_metadata()

    # ==================================================================================
    # Private metadata methods which retrieve metadata that are not closely linked to
    # the actual instance to be exported.

    def _get_meta_dollars(self) -> None:
        """Get metadata from the few $<some> from the fmuconfig file.

        $schema
        $version
        $source
        """

        if self._config is None:
            raise ValueError("Config is missing")

        dollars = ("$schema", "$version", "$source")

        for dollar in dollars:
            if not dollar in self._config.keys():
                raise ValueError(f"No {dollar} present in config.")

            self._meta_dollars[dollar] = self._config[dollar]

        logger.info("Metadata for $ variables are set!")
        return

    def _get_meta_masterdata(self) -> None:
        """Get metadata from masterdata section in config.

        Having the `masterdata` as hardcoded first level in the config is intentional.
        If that section is missing, or config is None, return with a user warning.

        """
        if self._config is None or "masterdata" not in self._config.keys():
            warnings.warn("No masterdata section present", UserWarning)
            self._meta_masterdata = None
            return

        self._meta_masterdata = self._config["masterdata"]
        logger.info("Metadata for masterdata is set!")

    def _get_meta_access(self) -> None:
        """Get metadata from access section in config."""
        if self._config is None or "access" not in self._config.keys():
            warnings.warn("No access section present", UserWarning)
            self._meta_access = None
            return

        self._meta_access = self._config["access"]
        logger.info("Metadata for access is set!")

    def _get_meta_tracklog(self) -> None:
        """Get metadata for tracklog section."""
        block = OrderedDict()
        block["datetime"] = datetime.datetime.now()
        block["user"] = {"user_id": getpass.getuser()}
        block["event"] = "created"

        self._meta_tracklog.append(block)
        logger.info("Metadata for tracklog is set")

    def _get_meta_fmu(self) -> None:
        """Get metadata for fmu key.

        The fmu block consist of these subkeys:
            model:
            workflow:
            element:
            realization OR aggradation:
            file:
            ensemble:
        """
        self._meta_fmu["model"] = self._process_meta_fmu_model()
        self._meta_fmu["workflow"] = self._details.get("workflow", None)
        self._meta_fmu["element"] = {"id": "15ce3b84-766f-4c93-9050-b154861f9100"}

        r_meta, e_meta = self._process_meta_fmu_realization_ensemble()
        self._meta_fmu["realization"] = r_meta
        self._meta_fmu["ensemble"] = e_meta
        logger.info("Metadata for realization and ensemble is parsed!")
        if r_meta is None and e_meta is None:
            logger.info(
                "Note that metadata for realization/ensemble are None, "
                "so this is interpreted as not an ERT run!"
            )

    def _process_meta_fmu_model(self):
        """Processing the fmu:model section."""

        # most of the info from global variables section model:
        meta = deepcopy(self._config["model"])

        # the model section in "template" contains root etc. For revision an
        # AUTO name may be used to avoid rapid and error-prone naming
        revision = meta.get("revision", "AUTO")
        if revision == "AUTO":
            rev = None
            folders = self._pwd
            for num in range(len(folders.parents)):
                thefolder = folders.parents[num].name

                # match 20.1.xxx style or r003 style
                if re.match("^[123][0-9]\\.", thefolder) or re.match(
                    "^[r][0-9][0-9][0-9]", thefolder
                ):
                    rev = thefolder
                    break

            meta["revision"] = rev

        logger.info("Got metadata for fmu:model")
        return meta

    def _process_meta_fmu_realization_ensemble(self):
        """Detect if this is a realization run.

        To detect if a realization run:
        * See of parameters.txt json at iter level
        * find iter name and realization number from folder names

        e.g.
        /scratch/xxx/user/case/realization-11/iter-3

        The iter folder may have other names, like "pred" which is fully
        supported. Then iter number shall be None.
        """
        is_fmurun = False

        r_meta = OrderedDict()
        e_meta = OrderedDict()

        folders = self._pwd
        therealization = None
        ertjob = OrderedDict()

        iterfolder = None
        casefolder = None
        userfolder = None

        for num in range(len(folders.parents)):
            thefolder = folders.parents[num].name
            if re.match("^realization-.", thefolder):
                is_fmurun = True
                iterfolder = pathlib.Path(self._pwd).resolve().parents[num - 1]
                casefolder = pathlib.Path(self._pwd).resolve().parents[num + 1]
                userfolder = pathlib.Path(self._pwd).resolve().parents[num + 2]

                logger.info("Realization folder is %s", thefolder)
                logger.info("Iter folder is %s", iterfolder.name)
                logger.info("Case folder is %s", casefolder.name)
                logger.info("User folder is %s", userfolder.name)
                therealization = thefolder.replace("realization-", "")

                parameters_file = iterfolder / "parameters.json"

                # store parameters.json and jobs.json
                if parameters_file.is_file():
                    with open(parameters_file, "r") as stream:
                        ertjob["params"] = json.load(stream)

                jobs_file = iterfolder / "jobs.json"
                if jobs_file.is_file():
                    with open(jobs_file, "r") as stream:
                        ertjob["jobs"] = json.load(stream)

        if not is_fmurun:
            return None, None

        # parse run_id from ERT
        erts = ertjob["jobs"]["run_id"].split(":")
        runid = ertjob["jobs"]["run_id"].replace(":", "_")
        timeid = erts[2]
        ensid = runid

        # populate the metadata for realization:
        r_meta["id"] = therealization
        r_meta["ert_id"] = runid + "--r" + therealization
        r_meta["jobs"] = ertjob["jobs"]
        r_meta["parameters"] = ertjob["params"]

        # populate the metadata for ensemble:
        e_meta["id"] = ensid
        theiter = None
        if iterfolder and re.match("^iter-.", iterfolder.name):
            logger.info("Realization folder is %s", thefolder)
            theiter = iterfolder.name.replace("iter-", "")

        if theiter is not None:
            e_meta["iteration"] = str(theiter)
        else:
            e_meta["iteration"] = None

        e_meta["iterfolder"] = iterfolder.name

        logger.info("Iteration is %s", e_meta["iteration"])

        e_meta["case"] = OrderedDict()
        hash_ = hashlib.md5((ertjob["jobs"]["DATA_ROOT"] + str(casefolder)).encode())
        hash_ = hash_.hexdigest()
        e_meta["case"]["id"] = hash_
        e_meta["case"]["data_root"] = ertjob["jobs"]["DATA_ROOT"]
        e_meta["case"]["runpath"] = casefolder
        e_meta["case"]["name"] = casefolder.name
        e_meta["user"] = OrderedDict()
        e_meta["user"]["user_id"] = userfolder.name
        e_meta["restart_from"] = None
        e_meta["description"] = [
            f"First ran by {getpass.getuser()} with ERT time ID: {timeid}"
        ]

        logger.info("Got metadata for fmu:realization")
        logger.debug("Realiz. meta: \n%s", json.dumps(r_meta, indent=2, default=str))
        logger.debug("Ensemble meta: \n%s", json.dumps(e_meta, indent=2, default=str))
        return r_meta, e_meta

    def _get_meta_strat(self) -> None:
        """Get metadata from the stratigraphy block in config; used indirectly."""

        if self._config is None or not "stratigraphy" in self._config:
            raise ValueError("Config is missing or stratigraphy block is missing")

        self._meta_strat = self._config["stratigraphy"]
        logger.info("Metadata for stratigraphy is parsed!")

    # ==================================================================================
    # Store ensemble data.
    # This is a hightly complicated issues, as ensembles can be reran with multiple
    # scenaria:
    # - Rerun failing realizations: ERT run_id and ert_pid will change but results
    #   shall appear as same ensemble
    # - Postrun part of workflow; typical on large fields. Ie. just run something
    #   that gives some new maps
    # - Change settings in RMS and just rerurn (will not be visible in ERT)
    #

    def _store_ensemble_metadata(self):
        if self._meta_fmu["ensemble"] is None:
            return

        ensemble_meta_exists = False

        runpath = self._meta_fmu["ensemble"]["case"]["runpath"]
        iterfolder = self._meta_fmu["ensemble"]["iterfolder"]

        share_ensroot = pathlib.Path(runpath) / "share" / "metadata" / iterfolder

        try:
            share_ensroot.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            ensemble_meta_exists = True

        metafile = share_ensroot / "fmu_ensemble.yml"

        # in case the file is deleted but the folder exists
        if not metafile.is_file():
            ensemble_meta_exists = False

        if not ensemble_meta_exists:
            # collect needed metadata and save to disk
            logger.info("Create ensemble_metadata as %s", str(metafile))
            meta = self._meta_dollars.copy()
            meta["access"] = self._meta_access
            meta["masterdata"] = self._meta_masterdata
            meta["fmu"] = OrderedDict()
            meta["fmu"]["ensemble"] = self._meta_fmu["ensemble"].copy()
            _utils.export_metadata_file(metafile, meta)

        else:
            # read the current metadatafile and compare ensemble id to issue a warning
            sleep(0.5)
            logger.info("Read existing ensemble metadata from %s", str(metafile))
            with open(metafile, "r") as stream:
                inmeta = yaml.safe_load(stream)

            id1 = self._meta_fmu["ensemble"]["id"]
            id2 = inmeta["fmu"]["ensemble"]["id"]

            if id1 != id2:
                warnings.warn("Ensemble metadata has changed, is this a rerun?")

            self._meta_access = inmeta["access"]
            self._meta_masterdata = inmeta["masterdata"]
            self._meta_fmu["ensemble"] = inmeta["fmu"]["ensemble"]

        # # In case the folder does not exist, populate with ensemeble metadata
        # meta = OrderedDict()
        # meta[""]

    # ==================================================================================
    # Public methods

    def to_file(self, obj: Any):
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

        """

        logger.info("Export to file...")
        if isinstance(obj, xtgeo.RegularSurface):
            _surface_io.surface_to_file(self, obj)
        elif isinstance(obj, xtgeo.Grid):
            _grid_io.grid_to_file(self, obj, None)
        elif isinstance(obj, xtgeo.GridProperty, None):
            _grid_io.grid_to_file(self, obj, prop=True, fformat=None)
