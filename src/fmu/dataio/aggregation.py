from __future__ import annotations

import copy
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Final, Literal, Optional, Union

from pydantic import ValidationError

from . import _utils, dataio, types
from ._logging import null_logger
from ._metadata import generate_meta_tracklog
from .providers.objectdata._provider import objectdata_provider_factory

logger: Final = null_logger(__name__)

# ######################################################################################
# AggregatedData
#
# The AggregatedData is used for making the aggregations from existing data that already
# have valid metadata, i.e. made from ExportData.
#
# Hence this is actually quite different and simpler than ExportData(), which
# needed a lot of info as FmuProvider, FileProvider, ObjectData etc. Here most these
# already known from the input.
#
# For aggregations, the id is normally given as an argument by the external process, and
# by that, be able to give a group of aggregations the same id.
#
# ######################################################################################


@dataclass
class AggregatedData:
    """Instantate AggregatedData object.

    Args:
        aggregation_id: Give an explicit ID for the aggregation. If None, an ID will be
        made based on existing realization uuids.
        casepath: The root folder to the case, default is None. If None, the casepath
            is derived from the first input metadata paths (cf. ``source_metadata``) if
            possible. If given explicitly, the physical casepath folder must exist in
            advance, otherwise a ValueError will be raised.
        source_metadata: A list of individual metadata dictionarys, coming from the
            valid metadata per input element that forms the aggregation.
        operation: A string that describes the operation, e.g. "mean". This is
            mandatory and there is no default.
        tagname: Additional name, as part of file name
    """

    # class variable(s)
    meta_format: ClassVar[Literal["yaml", "json"]] = "yaml"

    # instance
    aggregation_id: Optional[str] = None
    casepath: Optional[Union[str, Path]] = None
    source_metadata: list = field(default_factory=list)
    name: str = ""
    operation: str = ""
    tagname: str = ""
    verbosity: str = "DEPRECATED"  # keep for while

    _metadata: dict = field(default_factory=dict, init=False)
    _metafile: Path = field(default_factory=Path, init=False)

    def __post_init__(self) -> None:
        if self.verbosity != "DEPRECATED":
            warnings.warn(
                "Using the 'verbosity' key is now deprecated and will have no "
                "effect and will be removed in near future. Please remove it from the "
                "argument list. Set logging level from client script in the standard "
                "manner instead.",
                UserWarning,
            )

    @staticmethod
    def _generate_aggr_uuid(uuids: list[str]) -> str:
        """Unless aggregation_id; use existing UUIDs to generate a new UUID."""
        return str(_utils.uuid_from_string("".join(sorted(uuids))))

    def _update_settings(self, newsettings: dict) -> None:
        """Update instance settings (properties) from other routines."""
        logger.info("Try new settings %s", newsettings)

        # derive legal input from dataclass signature
        annots = getattr(self, "__annotations__", {})
        legals = {key: val for key, val in annots.items() if not key.startswith("_")}

        for setting, value in newsettings.items():
            if dataio._validate_variable(setting, value, legals):
                setattr(self, setting, value)
                logger.info("New setting OK for %s", setting)

    def _construct_filename(self, template: dict) -> tuple[Path, Path | None]:
        """Construct the paths/filenames for aggregated data.

        These filenames are constructed a bit different than in a forward job, since we
        do not now which folder we 'are in' when doing aggregations. Could possibly also
        be in a cloud setting.

        Hence we use the first input realization as template, e.g.:

        file:
           relative_path: realization-33/iter-0/share/results/maps/x.gri
           absolute_path: /scratch/f/case/realization-33/iter-0/share/results/maps/x.gri

        And from thet we derive/compose the relative and absolute path for the
        aggregated data:

        file:
           relative_path: iter-0/share/results/maps/aggr.gri
           absolute_path: /scratch/f/case/iter-0/share/results/maps/aggr.gri

        The trick is to replace 'realization-*' with nothing and create a new file
        name.

        -----
        However, there are also the scenario that absolute_path are missing (e.g. all
        input realizations are directly made in cloud setting), and we need to
        account for that:

        infile:
           relative_path: realization-33/iter-0/share/results/maps/x.gri
           absolute_path: none

        file:
           relative_path: iter-0/share/results/maps/aggr.gri
           absolute_path: none

        -----
        Finally, a user given casepath (casepath is not None) should replace the current
        root part in the files. Like this:

        infile:
           relative_path: realization-33/iter-0/share/results/maps/x.gri
           absolute_path: /scratch/f/case/realization-33/iter-0/share/results/maps/x.gri

        casepath = /scratch/f/othercase

        result:
           relative_path: iter-0/share/results/maps/aggr.gri
           absolute_path: /scratch/f/othercase/iter-0/share/results/maps/aggrd.gri

        """
        logger.info("Construct file name for the aggregation...")
        realiname = template["fmu"]["realization"]["name"]
        relpath = template["file"]["relative_path"]

        if template["file"].get("absolute_path", None):
            abspath = template["file"]["absolute_path"]
        else:
            abspath = None

        logger.info("First input realization relpath is: %s ", relpath)
        logger.info("First input realization abspath is: %s ", abspath)

        if self.casepath:
            casepath = Path(self.casepath)
            if not casepath.exists():
                raise ValueError(
                    f"The given casepath {casepath} does not exist. "
                    "It must exist in advance!"
                )
            abspath = str(casepath / relpath)

        relpath = relpath.replace(realiname + "/", "")
        relpath = Path(relpath)
        if abspath:
            abspath = abspath.replace(realiname + "/", "")
            abspath = Path(abspath)

        suffix = relpath.suffix
        stem = relpath.stem

        usename = stem + "--" + self.operation
        if not self.name:
            warnings.warn("Input name is not given, will assume <usename>", UserWarning)
        else:
            usename = self.name

        if self.tagname:
            usename = usename + "--" + self.tagname

        relname = (relpath.parent / usename).with_suffix(suffix)

        absname = None
        if abspath:
            absname = (abspath.parent / usename).with_suffix(suffix)

        logger.info("New relpath is: %s ", relname)
        logger.info("New abspath is: %s ", absname)

        return relname, absname

    def _generate_aggrd_metadata(
        self,
        obj: types.Inferrable,
        real_ids: list[int],
        uuids: list[str],
        compute_md5: bool = True,
    ) -> None:
        logger.info(
            "self.aggregation is %s (%s)",
            self.aggregation_id,
            type(self.aggregation_id),
        )

        if self.aggregation_id is None:
            self.aggregation_id = self._generate_aggr_uuid(uuids)
        else:
            if not isinstance(self.aggregation_id, str):
                raise ValueError("aggregation_id must be a string")

        if not self.operation:
            raise ValueError("The 'operation' key has no value")

        # use first as template but filter away invalid entries first:
        template = _utils.filter_validate_metadata(self.source_metadata[0])

        relpath, abspath = self._construct_filename(template)

        # fmu.realization shall not be used
        del template["fmu"]["realization"]

        template["fmu"]["aggregation"] = {}
        template["fmu"]["aggregation"]["operation"] = self.operation
        template["fmu"]["aggregation"]["realization_ids"] = real_ids
        template["fmu"]["aggregation"]["id"] = self.aggregation_id

        # fmu.context.stage should be 'iteration'
        template["fmu"]["context"]["stage"] = "iteration"

        # next, the new object will trigger update of: 'file', 'data' (some fields) and
        # 'tracklog'.

        # Make a temporary config from template to be allowed to
        # initialize a temporary ExportData without warnings so that we can get to the
        # objectdata_provider
        config = {
            "access": template["access"],
            "masterdata": template["masterdata"],
            "model": template["fmu"]["model"],
        }
        etemp = dataio.ExportData(config=config, name=self.name)

        objectdata_provider = objectdata_provider_factory(obj=obj, dataio=etemp)
        objdata = objectdata_provider.get_objectdata()

        template["tracklog"] = [generate_meta_tracklog()[0].model_dump(mode="json")]
        template["file"] = {
            "relative_path": str(relpath),
            "absolute_path": str(abspath) if abspath else None,
        }
        if compute_md5:
            template["file"]["checksum_md5"] = _utils.compute_md5_using_temp_file(
                obj, objdata.extension
            )

        # data section
        if self.name:
            template["data"]["name"] = self.name
        if self.tagname:
            template["data"]["tagname"] = self.tagname
        if bbox := objectdata_provider.get_bbox():
            template["data"]["bbox"] = bbox.model_dump(mode="json", exclude_none=True)

        self._metadata = template

    # ==================================================================================
    # Public methods:
    # ==================================================================================

    def generate_metadata(
        self,
        obj: types.Inferrable,
        compute_md5: bool = True,
        skip_null: bool = True,
        **kwargs: object,
    ) -> dict:
        """Generate metadata for the aggregated data.

        This is a quite different and much simpler operation than the ExportData()
        version, as here most metadata for each input element are already known. Hence,
        the metadata for the first element in the input list is used as template.

        Args:

            obj: The map, 3D grid, table, etc instance.

            compute_md5: If True, an md5 sum for the file will be created. This involves
                a temporary export of the data, and may be time consuming for large
                data.

            skip_null: If True (default), None values in putput will be skipped
            **kwargs: See AggregatedData() arguments; initial will be overridden by
                settings here.
        """
        logger.info("Generate metadata for class")
        self._update_settings(kwargs)

        # get input realization numbers:
        real_ids = []
        uuids = []
        for conf in self.source_metadata:
            try:
                rid = conf["fmu"]["realization"]["id"]
                xuuid = conf["fmu"]["realization"]["uuid"]
            except Exception as error:
                raise ValidationError(f"Seems that input config are not valid: {error}")

            real_ids.append(rid)
            uuids.append(xuuid)

        # first config file as template
        self._generate_aggrd_metadata(obj, real_ids, uuids, compute_md5)
        if skip_null:
            self._metadata = _utils.drop_nones(self._metadata)

        return copy.deepcopy(self._metadata)

    # alias method
    def generate_aggregation_metadata(
        self,
        obj: types.Inferrable,
        compute_md5: bool = True,
        skip_null: bool = True,
        **kwargs: object,
    ) -> dict:
        """Alias method name, see ``generate_metadata``"""
        return self.generate_metadata(
            obj, compute_md5=compute_md5, skip_null=skip_null, **kwargs
        )

    def export(self, obj: types.Inferrable, **kwargs: object) -> str:
        """Export aggregated file with metadata to file.

        Args:
            obj: Aggregated object to export, e.g. a XTGeo RegularSurface
            **kwargs: See AggregatedData() arguments; initial will be overridden by
                settings here.
        Returns:
            String: full path to exported item.
        """
        self._update_settings(kwargs)

        metadata = self.generate_metadata(obj, compute_md5=False)

        abspath = metadata["file"].get("absolute_path", None)

        if not abspath:
            raise OSError(
                "The absolute_path is None, hence no export is possible. "
                "Use the ``casepath`` key to provide a valid absolute path."
            )

        outfile = Path(abspath)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        metafile = outfile.parent / ("." + str(outfile.name) + ".yml")

        logger.info("Export to file and compute MD5 sum")
        # inject the computed md5 checksum in metadata
        metadata["file"]["checksum_md5"] = _utils.export_file_compute_checksum_md5(
            obj, outfile
        )

        _utils.export_metadata_file(metafile, metadata, savefmt=self.meta_format)
        logger.info("Actual file is:   %s", outfile)
        logger.info("Metadata file is: %s", metafile)

        self._metadata = metadata
        return str(outfile)
