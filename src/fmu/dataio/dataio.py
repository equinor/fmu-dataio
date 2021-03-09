"""Module for DataIO class."""
from typing import Union, Optional, Any
import pathlib
import re
from copy import deepcopy
from collections import OrderedDict

import warnings
import logging
import xtgeo

from . import _surface_io
from . import _grid_io

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


class ExportData:
    """Class for exporting data with rich metadata in FMU."""

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
        jobid: Optional[str] = "",
    ) -> None:
        """Instantate ExportData object."""
        self._project = project
        self._config = deepcopy(config)
        self._schema = schema
        self._fmustandard = fmustandard
        self._createfolder = createfolder
        self._content = content
        self._description = description
        self._jobid = jobid

        self._pwd = pathlib.Path().absolute()

        # define metadata for primary first order categories
        self._meta_data = OrderedDict()
        self._meta_master = OrderedDict()
        self._meta_fmu = OrderedDict()

        logger.setLevel(level=verbosity)

        # get the metadata at mastedata and fmu level; the data metadata will found
        # in to_file
        self._get_meta_master()
        self._get_meta_fmu()

        logger.info("Ran __init__")

    def to_file(
        self, obj: Any, fformat: Optional[str] = "hdf", content: Optional[str] = None
    ):
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
            fformat: File format, default is hdf for all datatypes. For other datatypes
                supported formats will be per class (e.g. irap_binary for
                RegularSurface and roff for GridProperty)

        """
        if content is not None:
            self._content = content

        if isinstance(obj, xtgeo.RegularSurface):
            _surface_io.surface_to_file(self, obj, fformat)
        elif isinstance(obj, xtgeo.Grid):
            _grid_io.grid_to_file(self, obj, fformat)
        elif isinstance(obj, xtgeo.GridProperty):
            _grid_io.grid_to_file(self, obj, fformat, prop=True)

    def _get_meta_master(self) -> None:
        """Get metadata from masterdata section in config.

        Having the `masterdata` as hardcoded first level in the config is intentional.
        If that section is missing, or config is None, return with a user warning.

        """
        if self._config is None or "masterdata" not in self._config.keys():
            warnings.warn("No masterdata section present", UserWarning)
            self._meta_master = None
            return

        logger.debug("Metadata FMU masterdata:\n%s", self._meta_master)
        logger.info("Metadata for FMU masterdata is set!")

    def _get_meta_fmu(self) -> None:
        """Get metadata from ensemble section or user spesified."""
        # WIP
        self._meta_fmu["template"] = self._process_meta_fmu_template()
        self._meta_fmu["ensemble"] = None  # TMP

    def _process_meta_fmu_template(self):
        """Processing the FMU template section."""
        meta = deepcopy(self._config["template"])

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

        return meta
