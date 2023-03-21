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
from os import environ
from pathlib import Path
from typing import Any, Optional
from warnings import warn

from fmu.config import utilities as ut

from . import _utils

# case metadata relative to rootpath
ERT2_RELATIVE_CASE_METADATA_FILE = "share/metadata/fmu_case.yml"
RESTART_PATH_ENVNAME = "RESTART_FROM_PATH"

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

    provider: Optional[str] = field(default=None, init=False)
    is_fmurun: Optional[bool] = field(default=False, init=False)
    iter_name: Optional[str] = field(default=None, init=False)
    iter_id: Optional[int] = field(default=None, init=False)
    iter_path: Optional[Path] = field(default=None, init=False)
    real_name: Optional[str] = field(default=None, init=False)
    real_id: int = field(default=0, init=False)
    real_path: Optional[Path] = field(default=None, init=False)
    case_name: Optional[str] = field(default=None, init=False)
    user_name: Optional[str] = field(default=None, init=False)
    ert2: dict = field(default_factory=dict, init=False)
    case_metafile: Optional[Path] = field(default=None, init=False)
    case_metadata: dict = field(default_factory=dict, init=False)
    metadata: dict = field(default_factory=dict, init=False)
    rootpath: Optional[Path] = field(default=None, init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)

        self.rootpath = Path(self.dataio._rootpath.absolute())

        self.rootpath_initial = self.rootpath

        logger.info("Initialize %s", __class__)

    def detect_provider(self):
        """First order method to detect provider, ans also check fmu_context."""
        if self._detect_ert2provider() or self._detect_ert2provider_case_only():
            self.provider = "ERT2"
            self.get_ert2_information()
            self.get_ert2_case_metadata()
            self.generate_ert2_metadata()
        else:
            logger.info("Detecting FMU provider as None")
            self.provider = None  # e.g. an interactive RMS run
            self.dataio._usecontext = None  # e.g. an interactive RMS run
            if self.dataio.fmu_context == "preprocessed":
                self.dataio._usecontext = self.dataio.fmu_context
            if self.dataio.fmu_context != self.dataio._usecontext:
                logger.warning(
                    "Requested fmu_context is <%s> but since this is detected as a non "
                    "FMU run, the actual context is set to <%s>",
                    self.dataio.fmu_context,
                    self.dataio._usecontext,
                )

    def _detect_ert2provider(self) -> bool:
        """Detect if ERT2 is provider and set itername, casename, etc.

        This is the pattern in a forward model, where realization etc exists.
        """
        logger.info("Try to detect ERT2 provider")

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
                    self.iter_id = None
                else:
                    raise ValueError("Could not derive iteration ID")

                self.iter_path = pathlib.Path(case_path / realfolder / iterfolder)
                self.real_path = pathlib.Path(case_path / realfolder)
                self.rootpath = case_path

                logger.info("Initial rootpath: %s", self.rootpath_initial)
                logger.info("Updated rootpath: %s", self.rootpath)

                logger.info("Detecting FMU provider as ERT2")
                return True

        return False

    def _detect_ert2provider_case_only(self) -> bool:
        """Detect ERT2 as provider when fmu_context is case'ish and casepath is given.

        This is typically found in ERT prehook work flows where case is establed by
        fmu.dataio.InitialiseCase() but no iter and realization folders exist. So
        only case-metadata are revelant here.
        """
        logger.info("Try to detect ERT2 provider (case context)")

        if (
            self.dataio.fmu_context
            and "case" in self.dataio.fmu_context
            and self.dataio.casepath
        ):
            self.rootpath = Path(self.dataio.casepath)

            folders = _get_folderlist(self.rootpath)
            logger.info("Folders to evaluate (case): %s", folders)

            self.iter_path = None
            self.real_path = None
            self.case_name = folders[-1]
            self.user_name = folders[-2]

            logger.info("Initial rootpath: %s", self.rootpath_initial)
            logger.info("Updated rootpath: %s", self.rootpath)
            logger.info("case_name, user_name: %s %s", self.case_name, self.user_name)

            logger.info("Detecting FMU provider as ERT2 (case only)")
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
        else:
            self.ert2["params"] = None
            logger.debug("parameters.txt was not found")

        # Load restart_from information
        if RESTART_PATH_ENVNAME in environ:
            logger.info("Detected a restart run from environment variable")
            restart_path = self.iter_path / environ[RESTART_PATH_ENVNAME]
            restart_iter = _get_folderlist(restart_path)[-1]
            restart_case_metafile = (
                restart_path / "../.." / ERT2_RELATIVE_CASE_METADATA_FILE
            ).resolve()
            if restart_case_metafile.exists():
                restart_metadata = ut.yaml_load(
                    restart_case_metafile, loader="standard"
                )
                self.ert2["restart_from"] = _utils.uuid_from_string(
                    restart_metadata["fmu"]["case"]["uuid"] + restart_iter
                )
            else:
                print(
                    f"{RESTART_PATH_ENVNAME} environment variable is set to "
                    "{environ[RESTART_PATH_ENVNAME]} which is invalid. Metadata "
                    "restart_from will remain empty."
                )
                logger.warning(
                    f"{RESTART_PATH_ENVNAME} environment variable is set to "
                    "{environ[RESTART_PATH_ENVNAME]} which is invalid. Metadata "
                    "restart_from will remain empty."
                )

        # store jobs.json if required!
        if self.dataio.include_ert2jobs:
            jobs_file = self.iter_path / "jobs.json"
            if jobs_file.is_file():
                with open(jobs_file, "r") as stream:
                    self.ert2["jobs"] = json.load(stream)
                logger.debug("jobs.json parsed.")
            logger.debug("jobs.json was not found")
        else:
            self.ert2["jobs"] = None
            logger.info("Storing jobs.json is disabled")

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
            self.case_metadata = ut.yaml_load(self.case_metafile, loader="standard")
            logger.info("Case metadata are now read!")
        else:
            logger.info(
                "Case metadata file does not exists as %s", str(self.case_metafile)
            )

    def generate_ert2_metadata(self):
        """Construct the metadata FMU block for an ERT2 forward job."""
        logger.info("Generate ERT2 metadata...")

        if not self.case_metadata:
            logger.info("Trigger UserWarning!")
            warn(
                f"The fmu provider: {self.provider} is found but no case metadata!",
                UserWarning,
            )

        meta = self.metadata  # shortform

        meta["model"] = self.dataio.config.get("model", None)

        meta["context"] = {"stage": self.dataio._usecontext}

        if self.dataio.workflow:
            if isinstance(self.dataio.workflow, str):
                meta["workflow"] = {"reference": self.dataio.workflow}
            elif isinstance(self.dataio.workflow, dict):
                if "reference" not in self.dataio.workflow:
                    raise ValueError(
                        "When workflow is given as a dict, the 'reference' "
                        "key must be included and be a string"
                    )
                warn(
                    "The 'workflow' argument should be given as a string. "
                    "Support for dictionary input is scheduled for deprecation.",
                    PendingDeprecationWarning,
                )

                meta["workflow"] = {"reference": self.dataio.workflow["reference"]}

            else:
                raise TypeError("'workflow' should be string.")

        case_uuid = "not_present"  # TODO! not allow missing case metadata?
        if self.case_metadata and "fmu" in self.case_metadata:
            meta["case"] = deepcopy(self.case_metadata["fmu"]["case"])
            case_uuid = meta["case"]["uuid"]

        if "realization" in self.dataio._usecontext:
            iter_uuid = _utils.uuid_from_string(case_uuid + str(self.iter_name))
            meta["iteration"] = {
                "id": self.iter_id,
                "uuid": iter_uuid,
                "name": self.iter_name,
                **(
                    {"restart_from": self.ert2["restart_from"]}
                    if "restart_from" in self.ert2
                    else {}
                ),
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
