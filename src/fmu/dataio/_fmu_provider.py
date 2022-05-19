"""Module for DataIO _FmuProvider

The FmuProvider will from the run environment and eventually API's detect valid
fields to the FMU data block.

Note that FMU may potentially have different providers, e.g. ERT2 vs ERT3
or it can detect that no providers are present (e.g. just ran from RMS interactive)
"""
import json
import logging
import pathlib
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from warnings import warn

from . import _utils

# case metadata relative to rootpath
ERT2_RELATIVE_CASE_METADATA_FILE = "share/metadata/fmu_case.yml"

logger = logging.getLogger(__name__)


def _get_folderlist(current: Path) -> list:
    """Return a list of pure folder names incl. current casepath up to system root.

    For example: current is /scratch/xfield/nn/case/realization-33/iter-1
    shall return ['', 'scratch', 'xfield', 'nn', 'case', 'realization-33', 'iter-1']
    """
    flist = [current.name]
    for par in current.parents:
        flist.append(par.name)

    flist.reverse()
    return flist


@dataclass
class _FmuProvider:
    """Class for detecting the run environment (e.g. an ERT2) and provide metadata."""

    dataio: Any
    verbosity: str = "CRITICAL"

    provider: str = field(default=None, init=False)
    is_fmurun: bool = field(default=False, init=False)
    iter_name: str = field(default=None, init=False)
    iter_id: int = field(default=None, init=False)
    iter_path: Path = field(default=None, init=False)
    real_name: str = field(default=None, init=False)
    real_id: int = field(default=0, init=False)
    real_path: Path = field(default=None, init=False)
    case_name: str = field(default=None, init=False)
    user_name: str = field(default=None, init=False)
    ert2: dict = field(default_factory=dict, init=False)
    case_metafile: Path = field(default=None, init=False)
    case_metadata: dict = field(default_factory=dict, init=False)
    metadata: dict = field(default_factory=dict, init=False)
    rootpath: Path = field(default=None, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)

        self.rootpath = Path(self.dataio._rootpath.absolute())

        self.rootpath_initial = self.rootpath

        logger.info("Initialize %s", __class__)

    def detect_provider(self):
        """First order method to detect provider."""
        if self._detect_ert2provider():
            logger.info("Detecting FMU provider as ERT2")
            self.provider = "ERT2"
            self.get_ert2_information()
            self.get_ert2_case_metadata()
            self.generate_ert2_metadata()
        else:
            logger.info("Detecting FMU provider as None")
            self.provider = None  # e.g. an interactive RMS run
            self.dataio._usecontext = None  # e.g. an interactive RMS run

    def _detect_ert2provider(self) -> bool:
        """Detect if ERT2 is provider and set itername, casename, etc."""

        folders = _get_folderlist(self.rootpath_initial)
        logger.info("Folders to evaluate: %s", folders)

        for num, folder in enumerate(folders):
            if folder and re.match("^realization-.", folder):
                self.is_fmurun = True
                realfolder = folders[num]
                iterfolder = folders[num + 1]
                casefolder = folders[num - 1]
                userfolder = folders[num - 2]

                case_path = Path("/".join(folders[0:num]))

                # override:
                if self.dataio.casepath:
                    case_path = Path(self.dataio.casepath)

                self.case_name = casefolder
                self.user_name = userfolder

                # store findings
                self.iter_name = iterfolder  # name of the folder

                # also derive the realization_id (realization number) from the folder
                self.real_id = int(realfolder.replace("realization-", ""))
                self.real_name = realfolder  # name of the realization folder

                # override realization if input key 'realization' is >= 0; only in rare
                # cases
                if self.dataio.realization and self.dataio.realization >= 0:
                    self.real_id = self.dataio.realization
                    self.real_name = "realization-" + str(self.real_id)

                # also derive iteration_id from the folder
                if "iter-" in str(iterfolder):
                    self.iter_id = int(iterfolder.replace("iter-", ""))
                elif isinstance(iterfolder, str):
                    # any custom name of the iteration, like "pred"
                    self.iter_id = 0
                else:
                    raise ValueError("Could not derive iteration ID")

                self.iter_path = pathlib.Path(case_path / realfolder / iterfolder)
                self.real_path = pathlib.Path(case_path / realfolder)
                self.rootpath = case_path

                logger.info("Initial rootpath: %s", self.rootpath_initial)
                logger.info("Updated rootpath: %s", self.rootpath)

                return True

        return False

    def get_ert2_information(self):
        """Retrieve information from an ERT2 run."""
        if not self.iter_path:
            return

        # store parameters.txt
        parameters_file = self.iter_path / "parameters.txt"
        if parameters_file.is_file():
            params = _utils.read_parameters_txt(parameters_file)
            nested_params = _utils.nested_parameters_dict(params)
            self.ert2["params"] = nested_params
            logger.debug("parameters.txt parsed.")
        logger.debug("parameters.txt was not found")

        # store jobs.json
        jobs_file = self.iter_path / "jobs.json"
        if jobs_file.is_file():
            with open(jobs_file, "r") as stream:
                self.ert2["jobs"] = json.load(stream)
            logger.debug("jobs.json parsed.")
        logger.debug("jobs.json was not found")

        logger.debug("ERT files has been parsed.")

    def get_ert2_case_metadata(self):
        """Check if metadatafile file for CASE exists, and if so parse metadata.

        If file does not exist, still give a proposed file path, but the
        self.case_metadata will be {} (empty) and the physical file will not be made.
        """

        self.case_metafile = self.rootpath / ERT2_RELATIVE_CASE_METADATA_FILE
        self.case_metafile = self.case_metafile.resolve()
        if self.case_metafile.exists():
            logger.info("Case metadata file exists at %s", str(self.case_metafile))
            self.case_metadata = _utils.load_yaml(self.case_metafile)
            logger.info("Case metadata are now read!")
        else:
            logger.info(
                "Case metadata file does not exists as %s", str(self.case_metafile)
            )

    def generate_ert2_metadata(self):
        """Construct the metadata FMU block for an ERT2 forward job."""
        logger.info("Generate ERT2 metadata...")

        if not self.case_metadata:
            warn(
                f"The fmu provider: {self.provider} is found but no case metadata!",
                UserWarning,
            )

        meta = self.metadata  # shortform

        meta["model"] = self.dataio.config.get("model", None)

        meta["context"] = {"stage": self.dataio._usecontext}

        if self.dataio.workflow:
            meta["workflow"] = {"reference": self.dataio.workflow}

        case_uuid = "not_present"  # TODO! not allow missing case metadata?
        if self.case_metadata and "fmu" in self.case_metadata:
            meta["case"] = deepcopy(self.case_metadata["fmu"]["case"])
            case_uuid = meta["case"]["uuid"]

        if "realization" in self.dataio._usecontext:
            iter_uuid = _utils.uuid_from_string(case_uuid + str(self.iter_id))
            meta["iteration"] = {
                "id": self.iter_id,
                "uuid": iter_uuid,
                "name": self.iter_name,
            }

            real_uuid = _utils.uuid_from_string(
                case_uuid + str(iter_uuid) + str(self.real_id)
            )

            logger.info(
                "Generate ERT2 metadata continues, and real ID %s", self.real_id
            )

            mreal = meta["realization"] = dict()
            mreal["id"] = self.real_id
            mreal["uuid"] = real_uuid
            mreal["name"] = self.real_name
            mreal["parameters"] = self.ert2["params"]
            mreal["jobs"] = self.ert2["jobs"]
