from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any, Final

from fmu.dataio._export_config import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import md5sum
from fmu.dataio.providers._base import Provider
from fmu.dataio.providers._filedata import SharePathConstructor
from fmu.dataio.providers.objectdata._export_models import (
    UnsetData,
)
from fmu.datamodels.fmu_results.data import AnyData, Time, Timestamp
from fmu.datamodels.fmu_results.global_configuration import (
    GlobalConfiguration,
    StratigraphyElement,
)

if TYPE_CHECKING:
    from fmu.dataio.types import Inferrable
    from fmu.datamodels.fmu_results.data import (
        BoundingBox2D,
        BoundingBox3D,
        Geometry,
    )
    from fmu.datamodels.fmu_results.enums import (
        FileFormat,
        Layout,
        MetadataClass,
    )
    from fmu.datamodels.fmu_results.specification import AnySpecification
    from fmu.datamodels.fmu_results.standard_result import StandardResult

logger: Final = null_logger(__name__)


@dataclass
class ObjectDataProvider(Provider):
    """Base class for providing metadata for data objects in fmu-dataio, e.g. a surface.

    The metadata for the 'data' are constructed by:

    * Investigating (parsing) the object (e.g. a XTGeo RegularSurface) itself
    * Combine the object info with user settings, globalconfig and class variables
    * OR
    * investigate current metadata if that is provided
    """

    # input fields
    obj: Inferrable
    export_config: ExportConfig
    standard_result: StandardResult | None = None

    # result properties; the most important is metadata which IS the 'data' part in
    # the resulting metadata. But other variables needed later are also given
    # as instance properties in addition (for simplicity in other classes/functions)
    _metadata: AnyData | UnsetData | None = field(default=None)
    name: str = field(default="")
    time0: datetime | None = field(default=None)
    time1: datetime | None = field(default=None)

    def __post_init__(self) -> None:
        if self.export_config.forcefolder:
            if self.export_config.forcefolder.startswith("/"):
                raise ValueError("Can't use absolute path as 'forcefolder'")
            logger.info(f"Using forcefolder {self.export_config.forcefolder}")

        content = self.export_config.content
        content_metadata = self.export_config.content_metadata

        strat_element = self._get_stratigraphy_element()
        self.name = strat_element.name

        metadata: dict[str, Any] = {}
        metadata["name"] = self.name
        metadata["stratigraphic"] = strat_element.stratigraphic
        metadata["offset"] = strat_element.offset
        metadata["alias"] = strat_element.alias
        metadata["top"] = strat_element.top
        metadata["base"] = strat_element.base

        metadata["content"] = content
        if content_metadata:
            metadata[content] = content_metadata
        metadata["standard_result"] = self.standard_result
        metadata["tagname"] = self.export_config.tagname
        metadata["format"] = self.fmt
        metadata["layout"] = self.layout
        metadata["unit"] = self.export_config.unit or ""
        metadata["vertical_domain"] = self.export_config.vertical_domain
        metadata["domain_reference"] = self.export_config.domain_reference

        metadata["spec"] = self.get_spec()
        metadata["geometry"] = self.get_geometry()
        metadata["bbox"] = self.get_bbox()
        metadata["time"] = self._get_timedata()
        metadata["table_index"] = self.table_index
        metadata["undef_is_zero"] = self.export_config.undef_is_zero

        metadata["is_prediction"] = self.export_config.is_prediction
        metadata["is_observation"] = self.export_config.is_observation
        metadata["description"] = self.export_config.description

        self._metadata = (
            UnsetData.model_validate(metadata)
            if metadata["content"] == "unset"
            else AnyData.model_validate(metadata)
        )
        logger.info("Derive all metadata for data object... DONE")

    @property
    @abstractmethod
    def classname(self) -> MetadataClass:
        raise NotImplementedError

    @property
    @abstractmethod
    def efolder(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def extension(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def fmt(self) -> FileFormat:
        raise NotImplementedError

    @property
    @abstractmethod
    def layout(self) -> Layout:
        raise NotImplementedError

    @property
    @abstractmethod
    def table_index(self) -> list[str] | None:
        raise NotImplementedError

    @abstractmethod
    def export_to_file(self, file: Path | BytesIO) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_geometry(self) -> Geometry | None:
        raise NotImplementedError

    @abstractmethod
    def get_bbox(self) -> BoundingBox2D | BoundingBox3D | None:
        raise NotImplementedError

    @abstractmethod
    def get_spec(self) -> AnySpecification | None:
        raise NotImplementedError

    @property
    def share_path(self) -> Path:
        return SharePathConstructor(self.export_config, self).get_share_path()

    def compute_md5_and_size(self) -> tuple[str, int]:
        """Compute an MD5 sum and the buffer size"""
        memory_stream = BytesIO()
        self.export_to_file(memory_stream)
        return md5sum(memory_stream), memory_stream.getbuffer().nbytes

    def compute_md5_and_size_using_temp_file(self) -> tuple[str, int]:
        """Compute an MD5 sum and the file size using a temporary file."""
        with NamedTemporaryFile(buffering=0, suffix=".tmp") as tf:
            logger.info("Compute MD5 sum for tmp file")
            tempfile = Path(tf.name)
            self.export_to_file(tempfile)
            return md5sum(tempfile), tempfile.stat().st_size

    def get_metadata(self) -> AnyData | UnsetData:
        assert self._metadata is not None
        return self._metadata

    def _get_stratigraphy_element(self) -> StratigraphyElement:
        """Derive the name and stratigraphy for the object; may have several sources.

        If not in input settings it is tried to be inferred from the xtgeo/pandas/...
        object. The name is then checked towards the stratigraphy list, and name is
        replaced with official stratigraphic name if found in static metadata
        `stratigraphy`. For example, if "TopValysar" is the model name and the actual
        name is "Valysar Top Fm." that latter name will be used.
        """
        name = ""
        if self.export_config.name:
            name = self.export_config.name
        elif isinstance(obj_name := getattr(self.obj, "name", ""), str):
            name = obj_name

        if (
            isinstance(self.export_config.config, GlobalConfiguration)
            and (strat := self.export_config.config.stratigraphy)
            and name in strat
        ):
            if (alias := strat[name].alias) is None:
                strat[name].alias = [name]
            elif name not in alias:
                alias.append(name)
            return strat[name]

        return StratigraphyElement(name=name)

    def _get_fmu_time_object(self, timedata_item: str | list[str]) -> Timestamp:
        """
        Returns a Timestamp from a timedata item on either string or
        list format: ["20200101", "monitor"] where the first item is a date and
        the last item is an optional label
        """

        if isinstance(timedata_item, list):
            value, *label = timedata_item
            return Timestamp(
                value=datetime.strptime(str(value), "%Y%m%d"),
                label=label[0] if label else None,
            )
        return Timestamp(
            value=datetime.strptime(str(timedata_item), "%Y%m%d"),
        )

    def _get_timedata(self) -> Time | None:
        """Format input timedata to metadata

        New format:
            When using two dates, input convention is
                -[[newestdate, "monitor"], [oldestdate,"base"]]
            but it is possible to turn around. But in the metadata the output t0
            shall always be older than t1 so need to check, and by general rule the file
            will be some--time1_time0 where time1 is the newest (unless a class
            variable is set for those who wants it turned around).
        """
        if not self.export_config.timedata:
            return None

        if not isinstance(self.export_config.timedata, list):
            raise ValueError("The 'timedata' argument should be a list")

        if len(self.export_config.timedata) > 2:
            raise ValueError("The 'timedata' argument can maximum contain two dates")

        start_input, *stop_input = self.export_config.timedata

        start = self._get_fmu_time_object(start_input)
        stop = self._get_fmu_time_object(stop_input[0]) if stop_input else None

        if stop:
            assert start and start.value is not None  # for mypy
            assert stop and stop.value is not None  # for mypy
            if start.value > stop.value:
                start, stop = stop, start

        self.time0, self.time1 = start.value, stop.value if stop else None

        return Time(t0=start, t1=stop)
