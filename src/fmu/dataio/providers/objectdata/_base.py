from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Final

from fmu.dataio._export_config import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import md5sum
from fmu.dataio.providers._base import Provider
from fmu.dataio.providers.objectdata._export_models import (
    UnsetData,
)
from fmu.datamodels.fmu_results.data import AnyData, SmdaEntity, Time, Timestamp
from fmu.datamodels.fmu_results.global_configuration import (
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


class ObjectDataProvider(Provider):
    """Base class for providing metadata for data objects in fmu-dataio, e.g. a surface.

    The metadata for the 'data' are constructed by:

    * Investigating (parsing) the object (e.g. a XTGeo RegularSurface) itself
    * Combine the object info with user settings, globalconfig and class variables
    * OR
    * investigate current metadata if that is provided
    """

    def __init__(
        self,
        obj: Inferrable,
        export_config: ExportConfig,
        standard_result: StandardResult | None = None,
    ) -> None:
        self.obj = obj
        self.export_config = export_config
        self.standard_result = standard_result

        self._validate_config()
        self._strat_element = self._resolve_stratigraphy()
        self._time = self._resolve_timedata()
        self._metadata = self._build_metadata()

    # TODO: Move to _export_config.
    def _validate_config(self) -> None:
        """Validate export configuration."""
        if (ff := self.export_config.forcefolder) and ff.startswith("/"):
            raise ValueError("Can't use absolute path as 'forcefolder'")

    def _resolve_stratigraphy(self) -> StratigraphyElement:
        """Resolve name against stratigraphy configuration.

        Uses the explicit name from config if provided, otherwise falls back to the
        object name. If the name is found in stratigraphy, returns the full
        stratigraphic element with official naming.

        Args:
            obj_name: Name from the object (e.g., surface.name)

        Returns:
            StratigraphyElement with resolved name and metadata.
        """
        name = self.export_config.name or getattr(self.obj, "name", "") or ""

        config = self.export_config.config
        if config and (stratigraphy := config.stratigraphy) and name in stratigraphy:
            element = stratigraphy[name]
            # Ensure input name is in aliases
            if element.alias is None:
                element.alias = [name]
            elif name not in element.alias:
                element.alias.append(name)
            return element

        return StratigraphyElement(name=name)

    # TODO: Move to _export_config
    def _resolve_timedata(self) -> Time | None:
        """Parse timedata into Time model."""
        timedata = self.export_config.timedata
        if not timedata:
            return None

        if not isinstance(timedata, list):
            raise ValueError("'timedata' must be a list")

        if len(timedata) > 2:
            raise ValueError("'timedata' can contain at most two dates")

        timestamps = [self._parse_timestamp(t) for t in timedata]

        # Ensure t0 <= t1
        if len(timestamps) == 2 and timestamps[0].value > timestamps[1].value:
            timestamps.reverse()

        return Time(
            t0=timestamps[0],
            t1=timestamps[1] if len(timestamps) == 2 else None,
        )

    @staticmethod
    def _parse_timestamp(item: str | list[str]) -> Timestamp:
        """Parse a timedata item into a Timestamp."""
        if isinstance(item, list):
            value, *label = item
            return Timestamp(
                value=datetime.strptime(str(value), "%Y%m%d"),
                label=label[0] if label else None,
            )
        return Timestamp(value=datetime.strptime(str(item), "%Y%m%d"))

    def _build_metadata(self) -> AnyData | UnsetData:
        """Build the metadata model from resolved values."""
        cfg = self.export_config

        data = {
            # Stratigraphy
            "name": self._strat_element.name,
            "stratigraphic": self._strat_element.stratigraphic,
            "offset": self._strat_element.offset,
            "alias": self._strat_element.alias,
            "top": self._strat_element.top,
            "base": self._strat_element.base,
            "smda_entity": self.smda_entity,
            # Content
            "content": cfg.content,
            "standard_result": self.standard_result,
            # Format
            "tagname": cfg.tagname,
            "format": self.fmt,
            "layout": self.layout,
            "unit": cfg.unit,
            "vertical_domain": cfg.vertical_domain,
            "domain_reference": cfg.domain_reference,
            # Object-derived
            "spec": self.get_spec(),
            "geometry": self.get_geometry(),
            "bbox": self.get_bbox(),
            "time": self._time,
            "table_index": self.table_index,
            # Flags
            "undef_is_zero": cfg.undef_is_zero,
            "is_prediction": cfg.is_prediction,
            "is_observation": cfg.is_observation,
            "description": cfg.description,
        }

        if cfg.content_metadata:
            data[cfg.content] = cfg.content_metadata

        model = UnsetData if cfg.content == "unset" else AnyData
        return model.model_validate(data)

    @property
    def name(self) -> str:
        """The resolved name for this object."""
        return self._strat_element.name

    @property
    def smda_entity(self) -> SmdaEntity | None:
        """The smda_entity (name) for this object"""
        if self._strat_element.stratigraphic:
            return SmdaEntity(identifier=self.name)
        return None

    @property
    def time0(self) -> datetime | None:
        """The first (oldest) timestamp, if present."""
        if self._time and self._time.t0:
            return self._time.t0.value
        return None

    @property
    def time1(self) -> datetime | None:
        """The second (newest) timestamp, if present."""
        if self._time and self._time.t1:
            return self._time.t1.value
        return None

    def get_metadata(self) -> AnyData | UnsetData:
        """Return the constructed metadata."""
        return self._metadata

    def compute_md5_and_size(self) -> tuple[str, int]:
        """Compute MD5 sum and buffer size using in-memory buffer."""
        buffer = BytesIO()
        self.export_to_file(buffer)
        return md5sum(buffer), buffer.getbuffer().nbytes

    def compute_md5_and_size_using_temp_file(self) -> tuple[str, int]:
        """Compute MD5 sum and file size using a temporary file."""
        with NamedTemporaryFile(buffering=0, suffix=".tmp") as tf:
            path = Path(tf.name)
            self.export_to_file(path)
            return md5sum(path), path.stat().st_size

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
