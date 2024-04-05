from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, TypeVar
from warnings import warn

from fmu.dataio._definitions import ConfigurationError
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import generate_description
from fmu.dataio.datastructure._internal.internal import AllowedContent
from fmu.dataio.datastructure.meta import content

if TYPE_CHECKING:
    from fmu.dataio.dataio import ExportData
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
    alias: list[str]

    stratigraphic: bool
    stratigraphic_alias: list[str]

    offset: int
    base: str | None
    top: str | None


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


def get_fmu_time_object(timedata_item: list[str]) -> content.FMUTimeObject:
    """
    Returns a FMUTimeObject from a timedata item on list
    format: ["20200101", "monitor"] where the first item is a date and
    the last item is an optional label
    """
    value, *label = timedata_item
    return content.FMUTimeObject(
        value=datetime.strptime(str(value), "%Y%m%d"),
        label=label[0] if label else None,
    )


@dataclass
class ObjectDataProvider(ABC):
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

    def _derive_name_stratigraphy(self) -> DerivedNamedStratigraphy:
        """Derive the name and stratigraphy for the object; may have several sources.

        If not in input settings it is tried to be inferred from the xtgeo/pandas/...
        object. The name is then checked towards the stratigraphy list, and name is
        replaced with official stratigraphic name if found in static metadata
        `stratigraphy`. For example, if "TopValysar" is the model name and the actual
        name is "Valysar Top Fm." that latter name will be used.
        """
        name = derive_name(self.dataio, self.obj)

        # next check if usename has a "truename" and/or aliases from the config
        strat = self.dataio.config.get("stratigraphy", {})
        no_start_or_missing_name = strat is None or name not in strat

        rv = DerivedNamedStratigraphy(
            name=name if no_start_or_missing_name else strat[name].get("name", name),
            alias=[] if no_start_or_missing_name else strat[name].get("alias", []),
            stratigraphic=False
            if no_start_or_missing_name
            else strat[name].get("stratigraphic", False),
            stratigraphic_alias=[]
            if no_start_or_missing_name
            else strat[name].get("stratigraphic_alias"),
            offset=0.0 if no_start_or_missing_name else strat[name].get("offset", 0.0),
            top=None if no_start_or_missing_name else strat[name].get("top"),
            base=None if no_start_or_missing_name else strat[name].get("base"),
        )

        if not no_start_or_missing_name and rv.name != "name":
            rv.alias.append(name)

        return rv

    def _process_content(self) -> tuple[str | dict, dict | None]:
        """Work with the `content` metadata"""

        # content == "unset" is not wanted, but in case metadata has been produced while
        # doing a preprocessing step first, and this step is re-using metadata, the
        # check is not done.
        if self.dataio._usecontent == "unset" and not self.dataio._reuse_metadata:
            allowed_fields = ", ".join(AllowedContent.model_fields.keys())
            warn(
                "The <content> is not provided which defaults to 'unset'. "
                "It is strongly recommended that content is given explicitly! "
                f"\n\nValid contents are: {allowed_fields} "
                "\n\nThis list can be extended upon request and need.",
                UserWarning,
            )

        content = self.dataio._usecontent
        content_spesific = None

        # Outgoing content is always a string, but it can be given as a dict if content-
        # specific information is to be included in the metadata.
        # In that case, it shall be inserted in the data block as a key with name as the
        # content, e.g. "seismic" or "field_outline"
        if self.dataio._content_specific is not None:
            content_spesific = self.dataio._content_specific

        return content, content_spesific

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

        return content.Time(t0=start, t1=stop).model_dump(
            mode="json", exclude_none=True
        )

    @abstractmethod
    def get_spec(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_bbox(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_objectdata(self) -> DerivedObjectDescriptor:
        raise NotImplementedError

    def derive_metadata(self) -> None:
        """Main function here, will populate the metadata block for 'data'."""
        logger.info("Derive all metadata for data object...")

        namedstratigraphy = self._derive_name_stratigraphy()
        objres = self.get_objectdata()
        if self.dataio.forcefolder and not self.dataio.forcefolder.startswith("/"):
            msg = (
                f"The standard folder name is overrided from {objres.efolder} to "
                f"{self.dataio.forcefolder}"
            )
            objres.efolder = self.dataio.forcefolder
            logger.info(msg)
            warn(msg, UserWarning)

        meta = self.metadata  # shortform

        meta["name"] = namedstratigraphy.name
        meta["stratigraphic"] = namedstratigraphy.stratigraphic
        meta["offset"] = namedstratigraphy.offset
        meta["alias"] = namedstratigraphy.alias
        meta["top"] = namedstratigraphy.top
        meta["base"] = namedstratigraphy.base

        content, content_spesific = self._process_content()
        meta["content"] = content
        if content_spesific:
            meta[self.dataio._usecontent] = content_spesific

        meta["tagname"] = self.dataio.tagname
        meta["format"] = objres.fmt
        meta["layout"] = objres.layout
        meta["unit"] = self.dataio.unit
        meta["vertical_domain"] = list(self.dataio.vertical_domain.keys())[0]
        meta["depth_reference"] = list(self.dataio.vertical_domain.values())[0]
        meta["spec"] = objres.spec
        meta["bbox"] = objres.bbox
        meta["table_index"] = objres.table_index
        meta["undef_is_zero"] = self.dataio.undef_is_zero

        # timedata:
        meta["time"] = self._derive_timedata()
        meta["is_prediction"] = self.dataio.is_prediction
        meta["is_observation"] = self.dataio.is_observation
        meta["description"] = generate_description(self.dataio.description)

        # the next is to give addition state variables identical values, and for
        # consistency these are derived after all eventual validation and directly from
        # the self.metadata fields:

        self.name = meta["name"]

        # then there are a few settings that are not in the ``data`` metadata, but
        # needed as data/variables in other classes:

        self.efolder = objres.efolder
        self.classname = objres.classname
        self.extension = objres.extension
        self.fmt = objres.fmt
        logger.info("Derive all metadata for data object... DONE")

    @classmethod
    def from_metadata_dict(
        cls, obj: Inferrable, dataio: ExportData, meta_existing: dict
    ) -> ObjectDataProvider:
        """Instantiate from existing metadata."""

        relpath = Path(meta_existing["file"]["relative_path"])

        time0, time1 = None, None
        if "time" in meta_existing["data"]:
            time0, time1 = get_timedata_from_existing(meta_existing["data"]["time"])

        return cls(
            obj=obj,
            dataio=dataio,
            metadata=meta_existing["data"],
            name=meta_existing["data"]["name"],
            classname=meta_existing["class"],
            efolder=(
                relpath.parent.parent.name if dataio.subfolder else relpath.parent.name
            ),
            extension=relpath.suffix,
            fmt=meta_existing["data"]["format"],
            time0=time0,
            time1=time1,
        )
