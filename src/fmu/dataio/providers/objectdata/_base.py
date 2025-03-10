from __future__ import annotations

import warnings
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final

from fmu.dataio._definitions import ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.data import AnyData, Time, Timestamp
from fmu.dataio._models.fmu_results.enums import Content
from fmu.dataio._models.fmu_results.global_configuration import (
    GlobalConfiguration,
    StratigraphyElement,
)
from fmu.dataio._models.fmu_results.standard_result import StandardResult
from fmu.dataio._utils import generate_description
from fmu.dataio.exceptions import ConfigurationError
from fmu.dataio.providers._base import Provider
from fmu.dataio.providers.objectdata._export_models import (
    UnsetData,
    content_metadata_factory,
    content_requires_metadata,
    property_warn,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

    from fmu.dataio._models.fmu_results.data import (
        BoundingBox2D,
        BoundingBox3D,
        Geometry,
    )
    from fmu.dataio._models.fmu_results.enums import FileFormat, FMUClass, Layout
    from fmu.dataio._models.fmu_results.specification import AnySpecification
    from fmu.dataio.dataio import ExportData
    from fmu.dataio.types import Inferrable

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
    dataio: ExportData
    standard_result: StandardResult | None = None

    # result properties; the most important is metadata which IS the 'data' part in
    # the resulting metadata. But other variables needed later are also given
    # as instance properties in addition (for simplicity in other classes/functions)
    _metadata: AnyData | UnsetData | None = field(default=None)
    name: str = field(default="")
    time0: datetime | None = field(default=None)
    time1: datetime | None = field(default=None)

    def __post_init__(self) -> None:
        if self.dataio.forcefolder:
            if self.dataio.forcefolder.startswith("/"):
                raise ValueError("Can't use absolute path as 'forcefolder'")
            logger.info(f"Using forcefolder {self.dataio.forcefolder}")

        content = self.dataio._get_content_enum() or "unset"
        content_metadata = self._get_validated_content_metadata()

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
        metadata["tagname"] = self.dataio.tagname
        metadata["format"] = self.fmt
        metadata["layout"] = self.layout
        metadata["unit"] = self.dataio.unit or ""
        metadata["vertical_domain"] = self.dataio.vertical_domain
        metadata["domain_reference"] = self.dataio.domain_reference

        metadata["spec"] = self.get_spec()
        metadata["geometry"] = self.get_geometry()
        metadata["bbox"] = self.get_bbox()
        metadata["time"] = self._get_timedata()
        metadata["table_index"] = self.table_index
        metadata["undef_is_zero"] = self.dataio.undef_is_zero

        metadata["is_prediction"] = self.dataio.is_prediction
        metadata["is_observation"] = self.dataio.is_observation
        metadata["description"] = generate_description(self.dataio.description)

        self._metadata = (
            UnsetData.model_validate(metadata)
            if metadata["content"] == "unset"
            else AnyData.model_validate(metadata)
        )
        logger.info("Derive all metadata for data object... DONE")

    @property
    @abstractmethod
    def classname(self) -> FMUClass:
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
    def get_geometry(self) -> Geometry | None:
        raise NotImplementedError

    @abstractmethod
    def get_bbox(self) -> BoundingBox2D | BoundingBox3D | None:
        raise NotImplementedError

    @abstractmethod
    def get_spec(self) -> AnySpecification | None:
        raise NotImplementedError

    def get_metadata(self) -> AnyData | UnsetData:
        assert self._metadata is not None
        return self._metadata

    def _get_validated_content_metadata(self) -> BaseModel | None:
        """
        If content_metadata have been input, and the content requires metadata,
        return the corresponding validated content_metadata model for the content,
        else return None.
        """
        content = self.dataio._get_content_enum()
        if content:
            content_metadata = self.dataio._get_content_metadata()

            if content_requires_metadata(content):
                if not content_metadata:
                    return self._raise_error_for_missing_content_metadata(content)

                content_metadata_model = content_metadata_factory(content)
                if not isinstance(content_metadata, dict):
                    raise ValueError(
                        "The 'content_metadata' needs to be input as a dictionary. "
                        f"Possible keys for content '{content.value}' are: "
                        f"{list(content_metadata_model.model_fields)}. "
                    )
                return content_metadata_model.model_validate(content_metadata)

            if content_metadata:
                warnings.warn(
                    f"Content '{content.value}' does not require 'content_metadata', "
                    "ignoring input."
                )

        return None

    @staticmethod
    def _raise_error_for_missing_content_metadata(content: Content) -> None:
        """
        Raise error for missing content_metadata with special handling of the
        'property' content which is required to have content_metadata in the future.
        """
        if content == Content.property:
            property_warn()
        else:
            raise ValueError(f"Content {content.value} requires additional input")

    def _get_stratigraphy_element(self) -> StratigraphyElement:
        """Derive the name and stratigraphy for the object; may have several sources.

        If not in input settings it is tried to be inferred from the xtgeo/pandas/...
        object. The name is then checked towards the stratigraphy list, and name is
        replaced with official stratigraphic name if found in static metadata
        `stratigraphy`. For example, if "TopValysar" is the model name and the actual
        name is "Valysar Top Fm." that latter name will be used.
        """
        name = ""
        if self.dataio.name:
            name = self.dataio.name
        elif isinstance(obj_name := getattr(self.obj, "name", ""), str):
            name = obj_name

        if (
            isinstance(self.dataio.config, GlobalConfiguration)
            and (strat := self.dataio.config.stratigraphy)
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
        if not self.dataio.timedata:
            return None

        if not isinstance(self.dataio.timedata, list):
            raise ValueError("The 'timedata' argument should be a list")

        if len(self.dataio.timedata) > 2:
            raise ValueError("The 'timedata' argument can maximum contain two dates")

        start_input, *stop_input = self.dataio.timedata

        start = self._get_fmu_time_object(start_input)
        stop = self._get_fmu_time_object(stop_input[0]) if stop_input else None

        if stop:
            assert start and start.value is not None  # for mypy
            assert stop and stop.value is not None  # for mypy
            if start.value > stop.value:
                start, stop = stop, start

        self.time0, self.time1 = start.value, stop.value if stop else None

        return Time(t0=start, t1=stop)

    @staticmethod
    def _validate_get_ext(fmt: str, validator: ValidFormats) -> str:
        """Validate that fmt (file format) matches data and return legal extension."""
        try:
            return validator.value[fmt]
        except KeyError as e:
            raise ConfigurationError(
                f"The file format {fmt} is not supported. ",
                f"Valid formats are: {list(validator.value.keys())}",
            ) from e
