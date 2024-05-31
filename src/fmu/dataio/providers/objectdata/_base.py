from __future__ import annotations

from abc import abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final, TypeVar
from warnings import warn

from fmu.dataio._definitions import ConfigurationError
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import generate_description
from fmu.dataio.datastructure._internal.internal import AllowedContent, UnsetAnyContent
from fmu.dataio.datastructure.meta.content import (
    AnyContent,
    FMUTimeObject,
    Time,
)
from fmu.dataio.datastructure.meta.enums import ContentEnum
from fmu.dataio.providers._base import Provider

if TYPE_CHECKING:
    from fmu.dataio.dataio import ExportData
    from fmu.dataio.datastructure.meta.content import BoundingBox2D, BoundingBox3D
    from fmu.dataio.datastructure.meta.specification import AnySpecification
    from fmu.dataio.types import Classname, Efolder, Inferrable, Layout, Subtype

logger: Final = null_logger(__name__)

V = TypeVar("V")


@dataclass
class DerivedObjectDescriptor:
    subtype: Subtype
    classname: Classname
    layout: Layout
    efolder: Efolder | str
    fmt: str
    extension: str
    spec: dict[str, Any] | None
    bbox: dict[str, Any] | None
    table_index: list[str] | None


@dataclass
class DerivedNamedStratigraphy:
    name: str
    alias: list[str] = field(default_factory=list)

    stratigraphic: bool = field(default=False)
    stratigraphic_alias: list[str] = field(default_factory=list)

    offset: float = field(default=0.0)
    base: str | None = field(default=None)
    top: str | None = field(default=None)


def derive_name(
    export: ExportData,
    obj: Inferrable,
) -> str:
    """
    Derives and returns a name for an export operation based on the
    provided ExportData instance and a 'sniffable' object.
    """
    if name := export.name:
        return name

    if isinstance(name := getattr(obj, "name", ""), str):
        return name

    return ""


def get_timedata_from_existing(meta_timedata: dict) -> tuple[datetime, datetime | None]:
    """Converts the time data in existing metadata from a string to a datetime.

    The time section under datablock has variants to parse.

    Formats::
        "time": {
            "t0": {
               "value": "2022-08-02T00:00:00",
               "label": "base"
            }
        }

        # with or without t1
        # or legacy format:

        "time": [
        {
            "value": "2030-01-01T00:00:00",
            "label": "moni"
        },
        {
            "value": "2010-02-03T00:00:00",
            "label": "base"
        }
        ],
    """
    date1 = None
    if isinstance(meta_timedata, list):
        date0 = meta_timedata[0]["value"]
        if len(meta_timedata) == 2:
            date1 = meta_timedata[1]["value"]
    elif isinstance(meta_timedata, dict):
        date0 = meta_timedata["t0"].get("value")
        if "t1" in meta_timedata:
            date1 = meta_timedata["t1"].get("value")

    return (
        datetime.strptime(date0, "%Y-%m-%dT%H:%M:%S"),
        datetime.strptime(date1, "%Y-%m-%dT%H:%M:%S") if date1 else None,
    )


def get_fmu_time_object(timedata_item: list[str]) -> FMUTimeObject:
    """
    Returns a FMUTimeObject from a timedata item on list
    format: ["20200101", "monitor"] where the first item is a date and
    the last item is an optional label
    """
    value, *label = timedata_item
    return FMUTimeObject(
        value=datetime.strptime(str(value), "%Y%m%d"),
        label=label[0] if label else None,
    )


def get_validated_content(content: str | dict | None) -> AllowedContent:
    """Check content and return a validated model."""
    logger.info("Evaluate content")
    logger.debug("content is %s of type %s", str(content), type(content))

    if not content:
        return AllowedContent(content="unset")

    if isinstance(content, str):
        return AllowedContent(content=ContentEnum(content))

    if len(content) > 1:
        raise ValueError(
            "Found more than one content item in the 'content' dictionary. Ensure "
            "input is formatted as content={'mycontent': {extra_key: extra_value}}."
        )
    content = deepcopy(content)
    usecontent, content_specific = next(iter(content.items()))
    logger.debug("usecontent is %s", usecontent)
    logger.debug("content_specific is %s", content_specific)

    return AllowedContent.model_validate(
        {"content": ContentEnum(usecontent), "content_incl_specific": content}
    )


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

    # result properties; the most important is metadata which IS the 'data' part in
    # the resulting metadata. But other variables needed later are also given
    # as instance properties in addition (for simplicity in other classes/functions)
    metadata: dict = field(default_factory=dict)
    name: str = field(default="")
    classname: str = field(default="")
    efolder: str = field(default="")
    extension: str = field(default="")
    fmt: str = field(default="")
    time0: datetime | None = field(default=None)
    time1: datetime | None = field(default=None)

    def __post_init__(self) -> None:
        """Main function here, will populate the metadata block for 'data'."""

        # Don't re-initialize data if it's coming from pre-existing metadata.
        if self.metadata:
            return

        namedstratigraphy = self._derive_named_stratigraphy()
        objres = self.get_objectdata()
        content_model = get_validated_content(self.dataio.content)

        if self.dataio.forcefolder:
            if self.dataio.forcefolder.startswith("/"):
                raise ValueError("Can't use absolute path as 'forcefolder'")
            msg = (
                f"The standard folder name is overrided from {objres.efolder} to "
                f"{self.dataio.forcefolder}"
            )
            objres.efolder = self.dataio.forcefolder
            logger.info(msg)
            warn(msg, UserWarning)

        self.metadata["name"] = namedstratigraphy.name
        self.metadata["stratigraphic"] = namedstratigraphy.stratigraphic
        self.metadata["offset"] = namedstratigraphy.offset
        self.metadata["alias"] = namedstratigraphy.alias
        self.metadata["top"] = namedstratigraphy.top
        self.metadata["base"] = namedstratigraphy.base

        self.metadata["content"] = (usecontent := content_model.content)
        if content_model.content_incl_specific:
            self.metadata[usecontent] = getattr(
                content_model.content_incl_specific, usecontent, None
            )

        self.metadata["tagname"] = self.dataio.tagname
        self.metadata["format"] = objres.fmt
        self.metadata["layout"] = objres.layout
        self.metadata["unit"] = self.dataio.unit or ""
        self.metadata["vertical_domain"] = list(self.dataio.vertical_domain.keys())[0]
        self.metadata["depth_reference"] = list(self.dataio.vertical_domain.values())[0]
        self.metadata["spec"] = objres.spec
        self.metadata["bbox"] = objres.bbox
        self.metadata["table_index"] = objres.table_index
        self.metadata["undef_is_zero"] = self.dataio.undef_is_zero

        # timedata:
        self.metadata["time"] = self._derive_timedata()
        self.metadata["is_prediction"] = self.dataio.is_prediction
        self.metadata["is_observation"] = self.dataio.is_observation
        self.metadata["description"] = generate_description(self.dataio.description)

        # the next is to give addition state variables identical values, and for
        # consistency these are derived after all eventual validation and directly from
        # the self.metadata fields:

        self.name = self.metadata["name"]

        # then there are a few settings that are not in the ``data`` metadata, but
        # needed as data/variables in other classes:

        self.efolder = objres.efolder
        self.classname = objres.classname
        self.extension = objres.extension
        self.fmt = objres.fmt
        logger.info("Derive all metadata for data object... DONE")

    def _derive_named_stratigraphy(self) -> DerivedNamedStratigraphy:
        """Derive the name and stratigraphy for the object; may have several sources.

        If not in input settings it is tried to be inferred from the xtgeo/pandas/...
        object. The name is then checked towards the stratigraphy list, and name is
        replaced with official stratigraphic name if found in static metadata
        `stratigraphy`. For example, if "TopValysar" is the model name and the actual
        name is "Valysar Top Fm." that latter name will be used.
        """
        name = derive_name(self.dataio, self.obj)

        # next check if usename has a "truename" and/or aliases from the config
        stratigraphy = self.dataio.config.get("stratigraphy", {})

        if name not in stratigraphy:
            return DerivedNamedStratigraphy(name=name)

        named_stratigraphy = stratigraphy.get(name)
        rv = DerivedNamedStratigraphy(
            name=named_stratigraphy.get("name", name),
            alias=named_stratigraphy.get("alias", []),
            stratigraphic=named_stratigraphy.get("stratigraphic", False),
            stratigraphic_alias=named_stratigraphy.get("stratigraphic_alias", []),
            offset=named_stratigraphy.get("offset", 0.0),
            top=named_stratigraphy.get("top"),
            base=named_stratigraphy.get("base"),
        )
        if rv.name != "name":
            rv.alias.append(name)

        return rv

    def _derive_timedata(self) -> dict[str, str] | None:
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

        if len(self.dataio.timedata) > 2:
            raise ValueError("The 'timedata' argument can maximum contain two dates")

        start_input, *stop_input = self.dataio.timedata

        start = get_fmu_time_object(start_input)
        stop = get_fmu_time_object(stop_input[0]) if stop_input else None

        if stop:
            assert start and start.value is not None  # for mypy
            assert stop and stop.value is not None  # for mypy
            if start.value > stop.value:
                start, stop = stop, start

        self.time0, self.time1 = start.value, stop.value if stop else None

        return Time(t0=start, t1=stop).model_dump(mode="json", exclude_none=True)

    @abstractmethod
    def get_spec(self) -> AnySpecification | None:
        raise NotImplementedError

    @abstractmethod
    def get_bbox(self) -> BoundingBox2D | BoundingBox3D | None:
        raise NotImplementedError

    @abstractmethod
    def get_objectdata(self) -> DerivedObjectDescriptor:
        raise NotImplementedError

    def get_metadata(self) -> AnyContent | UnsetAnyContent:
        return (
            UnsetAnyContent.model_validate(self.metadata)
            if self.metadata["content"] == "unset"
            else AnyContent.model_validate(self.metadata)
        )

    @staticmethod
    def _validate_get_ext(fmt: str, subtype: str, validator: dict[str, V]) -> V:
        """Validate that fmt (file format) matches data and return legal extension."""
        try:
            return validator[fmt]
        except KeyError:
            raise ConfigurationError(
                f"The file format {fmt} is not supported. ",
                f"Valid {subtype} formats are: {list(validator.keys())}",
            )
