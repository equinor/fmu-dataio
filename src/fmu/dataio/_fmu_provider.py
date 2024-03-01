"""Module for DataIO FmuProvider

The FmuProvider will from the environment and eventually API's detect valid
fields to the FMU data block.

Note that FMU may potentially have different providers, e.g. ERT versions
or it can detect that no FMU providers are present (e.g. just ran from RMS interactive)

Note that establishing the FMU case metadata for a run, is currently *not* done
here; this is done by code in the InitializeCase class.

From ERT v. 5 (?), the following env variables are provided in startup (example):

_ERT_EXPERIMENT_ID:   6a8e1e0f-9315-46bb-9648-8de87151f4c7
_ERT_ENSEMBLE_ID:   b027f225-c45d-477d-8f33-73695217ba14
_ERT_SIMULATION_MODE:   test_run

and during a Forward model:

_ERT_EXPERIMENT_ID:   6a8e1e0f-9315-46bb-9648-8de87151f4c7
_ERT_ENSEMBLE_ID:   b027f225-c45d-477d-8f33-73695217ba14
_ERT_SIMULATION_MODE:   test_run
_ERT_ITERATION_NUMBER:   0
_ERT_REALIZATION_NUMBER:   0
_ERT_RUNPATH:   /scratch/fmu/jriv/01_drogon_ahm/realization-0/iter-0/

"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, auto
from os import environ
from pathlib import Path
from typing import Final, Optional
from warnings import warn

from fmu.config import utilities as ut

from . import _utils
from ._definitions import FmuContext
from ._logging import null_logger

# case metadata relative to casepath
ERT_RELATIVE_CASE_METADATA_FILE: Final = "share/metadata/fmu_case.yml"
RESTART_PATH_ENVNAME: Final = "RESTART_FROM_PATH"

logger: Final = null_logger(__name__)


class FmuEnv(Enum):
    EXPERIMENT_ID = auto()
    ENSEMBLE_ID = auto()
    SIMULATION_MODE = auto()
    REALIZATION_NUMBER = auto()
    ITERATION_NUMBER = auto()
    RUNPATH = auto()

    @property
    def value(self) -> str | None:
        # Fetch the environment variable; name of the enum member prefixed with _ERT_
        return os.getenv(f"_ERT_{self.name}")

    @property
    def keyname(self) -> str:
        # Fetch the environment variable; name of the enum member prefixed with _ERT_
        return f"_ERT_{self.name}"


@dataclass
class FmuProvider:
    """Class for detecting the run environment (e.g. an ERT) and provide metadata.

    Args:
        model: Name of the model (usually from global config)
        rootpath: ....
        fmu_context: The FMU context this is ran in; see FmuContext enum class
        casepath_proposed: Proposed casepath ... needed?
        include_ertjobs: True if we want to include ....
        forced_realization: If we want to force the realization (use case?)
        workflow: Descriptive work flow info
    """

    model: str = ""
    fmu_context: FmuContext = FmuContext.REALIZATION
    include_ertjobs: bool = True
    casepath_proposed: str | Path = ""
    forced_realization: Optional[int] = None
    workflow: str | dict = ""

    # private properties for this class
    _stage: str = field(default="unset", init=False)
    _runpath: Path | str = field(default="", init=False)
    _casepath: Path | str = field(default="", init=False)  # actual casepath
    _provider: str = field(default="", init=False)
    _iter_name: str = field(default="", init=False)
    _iter_id: int = field(default=0, init=False)
    _iter_path: Path | str = field(default="", init=False)
    _real_name: str = field(default="", init=False)
    _real_id: int = field(default=0, init=False)
    _real_path: Path | str = field(default="", init=False)
    _case_name: str = field(default="", init=False)
    _user_name: str = field(default="", init=False)
    _ert_info: dict = field(default_factory=dict, init=False)
    _case_metadata: dict = field(default_factory=dict, init=False)
    _metadata: dict = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        logger.info("Initialize %s...", self.__class__)
        logger.debug("Case path is initially <%s>...", self.casepath_proposed)
        logger.debug("FMU context is <%s>...", self.fmu_context)

        if not FmuEnv.ENSEMBLE_ID.value:
            return  # not an FMU run

        self._provider = "ERT"

        self._detect_fmurun_stage()
        self._detect_absolute_runpath()
        self._detect_and_update_casepath()
        self._parse_folder_info()
        self._read_case_metadata()

        # the next ones will not be read if case metadata is empty, or stage is FMU CASE
        self._read_optional_restart_data()
        self._read_ert_information()
        self._generate_ert_metadata()

    def get_iter_name(self) -> str:
        """The client (metadata) will ask for iter_name"""
        """Return the iter_name, e.g. 'iter-3' or 'pred'."""
        return self._iter_name

    def get_real_name(self) -> str:
        """Return the real_name, e.g. 'realization-23'."""
        return self._real_name

    def get_casepath(self) -> str:
        """Return updated casepath in a FMU run, will be updated if initially blank."""
        return "" if not self._casepath else str(self._casepath)

    def get_provider(self) -> str | None:
        """Return the name of the FMU provider (so far 'ERT' only), or None."""
        return None if not self._provider else self._provider

    def get_metadata(self) -> dict:
        """The client (metadata) will ask for complete metadata for FMU section"""
        return {} if not self._metadata else self._metadata

    # private methods:
    @staticmethod
    def _get_folderlist_from_path(current: Path | str) -> list:
        """Return a list of pure folder names incl. current casepath up to system root.

        For example: current is /scratch/xfield/nn/case/realization-33/iter-1
        shall return ['scratch', 'xfield', 'nn', 'case', 'realization-33', 'iter-1']
        """
        return [folder for folder in str(current).split("/") if folder]

    @staticmethod
    def _get_folderlist_from_runpath_env() -> list:
        """Return a list of pure folder names incl. current from RUNPATH environment,

        Derived from _ERT_RUNPATH.

        For example: runpath is /scratch/xfield/nn/case/realization-33/iter-1/
        shall return ['scratch', 'xfield', 'nn', 'case', 'realization-33', 'iter-1']
        """
        runpath = FmuEnv.RUNPATH.value
        if runpath:
            return [folder for folder in runpath.split("/") if folder]
        return []

    def _detect_fmurun_stage(self) -> None:
        """Detect if ERT is in a PRE-HOOK or in a FORWARD MODEL stage

        Update self._stage = "case" | "forward" | "unset"
        """
        if FmuEnv.EXPERIMENT_ID.value and not FmuEnv.RUNPATH.value:
            self._stage = "case"
        elif FmuEnv.EXPERIMENT_ID.value and FmuEnv.RUNPATH.value:
            self._stage = "realization"
        else:
            self._stage = "unset"
        logger.debug("Detecting FMU stage as %s", self._stage)

    def _detect_absolute_runpath(self) -> None:
        """In case _ERT_RUNPATH is relative, an absolute runpath is detected."""
        if FmuEnv.RUNPATH.value:
            self._runpath = Path(FmuEnv.RUNPATH.value).resolve()

    def _detect_and_update_casepath(self) -> None:
        """If casepath is not given, then try update _casepath (if in realization).

        There is also a validation here that casepath contains case metadata, and if not
        then a second guess  is attempted, looking at `parent` insted of `parent.parent`
        is case of unconventional structure.
        """
        logger.debug("Try detect casepath, RUNPATH is %s", self._runpath)
        logger.debug("Proposed casepath is now <%s>", self.casepath_proposed)

        self._casepath = Path(self.casepath_proposed) if self.casepath_proposed else ""
        if self._stage == "case" and self._casepath:
            try_casepath = Path(self._casepath)
            logger.debug("Try casepath (stage is case): %s", try_casepath)

        elif not self._casepath:
            try_casepath = Path(self._runpath).parent.parent
            logger.debug("Try casepath (first attempt): %s", try_casepath)

            if not (try_casepath / ERT_RELATIVE_CASE_METADATA_FILE).exists():
                logger.debug("Cannot find metadata file, try just one parent...")
                try_casepath = Path(self._runpath).parent
                logger.debug("Try casepath (second attempt): %s", try_casepath)
            self._casepath = try_casepath

        if not (Path(self._casepath) / ERT_RELATIVE_CASE_METADATA_FILE).exists():
            logger.debug("No case metadata, issue a warning!")
            warn(
                "Case metadata does not exist; will not update initial casepath",
                UserWarning,
            )
            self._casepath = ""

    def _parse_folder_info(self) -> None:
        """Retreive the folders (id's and paths)."""
        logger.debug("Parse folder info...")

        folders = self._get_folderlist_from_runpath_env()
        if self.fmu_context == FmuContext.CASE and self._casepath:
            folders = self._get_folderlist_from_path(self._casepath)  # override
            logger.debug("Folders to evaluate (case): %s", folders)

            self._iter_path = ""
            self._real_path = ""
            self._case_name = folders[-1]
            self._user_name = folders[-2]

            logger.debug(
                "case_name, user_name: %s %s", self._case_name, self._user_name
            )
            logger.debug("Detecting FMU provider as ERT (case only)")
        else:
            logger.debug("Folders to evaluate (realization): %s", folders)

            self._case_name = folders[-3]
            self._user_name = folders[-4]

            self._iter_name = folders[-1]
            self._real_name = folders[-2]

            self._iter_path = Path("/" + "/".join(folders))
            self._real_path = Path("/" + "/".join(folders[:-1]))

            self._iter_id = int(str(FmuEnv.ITERATION_NUMBER.value))
            self._real_id = int(str(FmuEnv.REALIZATION_NUMBER.value))

    def _read_case_metadata(self) -> None:
        """Check if metadatafile file for CASE exists, and if so parse metadata.

        If file does not exist, still give a proposed file path, but the
        self.casepath_proposed_metadata will be {} (empty) and the physical file
        will not be made.
        """
        logger.debug("Read case metadata, if any...")
        if not self._casepath:
            logger.info("No case path detected, hence FMU metadata will be empty.")
            return

        case_metafile = Path(self._casepath) / ERT_RELATIVE_CASE_METADATA_FILE
        if case_metafile.exists():
            logger.debug("Case metadata file exists in file %s", str(case_metafile))
            self._case_metadata = ut.yaml_load(case_metafile, loader="standard")
            logger.debug("Case metadata are: %s", self._case_metadata)
        else:
            logger.debug("Case metadata file does not exists as %s", str(case_metafile))
            warn(
                "Cannot read case metadata, hence stop retrieving FMU data!",
                UserWarning,
            )
            self._case_metadata = {}

    def _read_optional_restart_data(self) -> None:
        # Load restart_from information
        logger.debug("Read optional restart data, if any, and requested...")
        if not self._case_metadata:
            return

        if not environ.get(RESTART_PATH_ENVNAME):
            return

        logger.debug("Detected a restart run from environment variable")
        restart_path = Path(self._iter_path) / environ[RESTART_PATH_ENVNAME]
        restart_iter = self._get_folderlist_from_path(restart_path)[-1]
        restart_case_metafile = (
            restart_path / "../.." / ERT_RELATIVE_CASE_METADATA_FILE
        ).resolve()
        if restart_case_metafile.exists():
            restart_metadata = ut.yaml_load(restart_case_metafile, loader="standard")
            self._ert_info["restart_from"] = _utils.uuid_from_string(
                restart_metadata["fmu"]["case"]["uuid"] + restart_iter
            )
        else:
            print(
                f"{RESTART_PATH_ENVNAME} environment variable is set to "
                f"{environ[RESTART_PATH_ENVNAME]} which is invalid. Metadata "
                "restart_from will remain empty."
            )
            logger.warning(
                f"{RESTART_PATH_ENVNAME} environment variable is set to "
                f"{environ[RESTART_PATH_ENVNAME]} which is invalid. Metadata "
                "restart_from will remain empty."
            )

    def _read_ert_information(self) -> None:
        """Retrieve information from an ERT (ver 5 and later) run."""
        logger.debug("Read ERT information, if any")

        if not self._case_metadata:
            return

        logger.debug("Read ERT information")
        if not self._iter_path:
            logger.debug("Not _iter_path!")
            return

        # store parameters.txt
        logger.debug("Read ERT information, if any (continues)")
        parameters_file = Path(self._iter_path) / "parameters.txt"
        if parameters_file.is_file():
            params = _utils.read_parameters_txt(parameters_file)
            # BUG(?): value can contain Nones, loop in fn. below
            # does contains check, will fail.
            nested_params = _utils.nested_parameters_dict(params)  # type: ignore
            self._ert_info["params"] = nested_params
            logger.debug("parameters.txt parsed.")
        else:
            self._ert_info["params"] = {}
            warn("The parameters.txt file was not found", UserWarning)

        # store jobs.json if required!
        if self.include_ertjobs:
            jobs_file = Path(self._iter_path) / "jobs.json"
            if jobs_file.is_file():
                with open(jobs_file) as stream:
                    self._ert_info["jobs"] = json.load(stream)
                logger.debug("jobs.json parsed.")
            else:
                logger.debug("jobs.json was not found")
        else:
            self._ert_info["jobs"] = None
            logger.debug("Storing jobs.json is disabled")

        logger.debug("ERT files has been parsed.")

    def _generate_ert_metadata(self) -> None:
        """Construct the metadata FMU block for an ERT forward job."""
        if not self._case_metadata:
            return

        logger.debug("Generate ERT metadata...")
        if not self._case_metadata:
            logger.debug("Trigger UserWarning!")
            warn(
                f"The fmu provider: {self._provider} is found but no case metadata!",
                UserWarning,
            )

        meta = self._metadata  # shortform

        meta["model"] = self.model

        meta["context"] = {"stage": self.fmu_context.name.lower()}

        if self.workflow:
            if isinstance(self.workflow, str):
                meta["workflow"] = {"reference": self.workflow}
            elif isinstance(self.workflow, dict):
                if "reference" not in self.workflow:
                    raise ValueError(
                        "When workflow is given as a dict, the 'reference' "
                        "key must be included and be a string"
                    )
                warn(
                    "The 'workflow' argument should be given as a string. "
                    "Support for dictionary input is scheduled for deprecation.",
                    PendingDeprecationWarning,
                )

                meta["workflow"] = {"reference": self.workflow["reference"]}

            else:
                raise TypeError("'workflow' should be string.")

        case_uuid = "not_present"  # TODO! not allow missing case metadata?
        if self._case_metadata and "fmu" in self._case_metadata:
            meta["case"] = deepcopy(self._case_metadata["fmu"]["case"])
            case_uuid = meta["case"]["uuid"]

        if self.fmu_context == FmuContext.REALIZATION:
            iter_uuid = _utils.uuid_from_string(case_uuid + str(self._iter_name))
            meta["iteration"] = {
                "id": self._iter_id,
                "uuid": iter_uuid,
                "name": self._iter_name,
                **(
                    {"restart_from": self._ert_info["restart_from"]}
                    if "restart_from" in self._ert_info
                    else {}
                ),
            }
            real_uuid = _utils.uuid_from_string(
                case_uuid + str(iter_uuid) + str(self._real_id)
            )

            logger.debug(
                "Generate ERT metadata continues, and real ID %s", self._real_id
            )

            mreal = meta["realization"] = {}
            mreal["id"] = self._real_id
            mreal["uuid"] = real_uuid
            mreal["name"] = self._real_name
            mreal["parameters"] = self._ert_info["params"]

            if self.include_ertjobs:
                mreal["jobs"] = self._ert_info["jobs"]
