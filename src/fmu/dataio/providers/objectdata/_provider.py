"""Module for DataIO _ObjectData

This contains evaluation of the valid objects that can be handled and is mostly used
in the ``data`` block but some settings are applied later in the other blocks

Example data block::

data:

    # if stratigraphic, name must match the strat column; official name of this surface.
    name: volantis_top-volantis_base
    stratigraphic: false  # if true, this is a stratigraphic surf found in strat column
    offset: 0.0  # to be used if a specific horizon is represented with an offset.

    top: # not required, but allowed
        name: volantis_gp_top
        stratigraphic: true
        offset: 2.0
    base:
        name: volantis_gp_top
        stratigraphic: true
        offset: 8.3

    stratigraphic_alias: # other stratigraphic entities this corresponds to
                         # in the strat column, e.g. Top Viking vs Top Draupne.
        - SomeName Fm. 1 Top
    alias: # other known-as names, such as name used inside RMS etc
        - somename_fm_1_top
        - top_somename

    # content is white-listed and standardized
    content: depth

    # tagname is flexible. The tag is intended primarily for providing uniqueness.
    # The tagname will also be part of the outgoing file name on disk.
    tagname: ds_extract_geogrid

    # no content-specific attribute for "depth" but can come in the future

    properties: # what the values actually show. List, only one for IRAP Binary
                # surfaces. Multiple for 3d grid or multi-parameter surfaces.
                # First is geometry.
        - name: PropertyName
          attribute: owc
          is_discrete: false # to be used for discrete values in surfaces.
          calculation: null # max/min/rms/var/maxpos/sum/etc

    format: irap_binary
    layout: regular # / cornerpoint / structured / etc
    unit: m
    vertical_domain: depth # / time / null
    depth_reference: msl # / seabed / etc # mandatory when vertical_domain is depth?
    grid_model: # Making this an object to allow for expanding in the future
        name: MyGrid # important for data identification, also for other data types
    spec: # class/layout dependent, optional? Can spec be expanded to work for all
          # data types?
        ncol: 281
        nrow: 441
        ...
    bbox:
        xmin: 456012.5003497944
        xmax: 467540.52762886323
        ...

    # --- NB two variants of time, here old:
    time:
        - value: 2029-10-28T11:21:12
          label: "some label"
        - value: 2020-10-28T14:28:02
          label: "some other label"

    # --- Here new:
    t0:
        value: 2020-10-28T14:28:02
        label: "some other label"
    t1:
        value: 2029-10-28T11:21:12
        label: "some label"

    is_prediction: true # For separating pure QC output from actual predictions
    is_observation: true # Used for 4D data currently but also valid for other data?
    description:
        - Depth surfaces extracted from the structural model

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pandas as pd
import xtgeo

from fmu.dataio._definitions import ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio.datastructure.meta.enums import FMUClassEnum
from fmu.dataio.readers import FaultRoomSurface

from ._base import (
    DerivedObjectDescriptor,
    ObjectDataProvider,
)
from ._faultroom import FaultRoomSurfaceProvider
from ._tables import ArrowTableDataProvider, DataFrameDataProvider
from ._xtgeo import (
    CPGridDataProvider,
    CPGridPropertyDataProvider,
    CubeDataProvider,
    PointsDataProvider,
    PolygonsDataProvider,
    RegularSurfaceDataProvider,
)

if TYPE_CHECKING:
    from fmu.dataio.dataio import ExportData
    from fmu.dataio.types import Inferrable

logger: Final = null_logger(__name__)


def objectdata_provider_factory(
    obj: Inferrable, dataio: ExportData, meta_existing: dict | None = None
) -> ObjectDataProvider:
    """Factory function that generates metadata for a particular data object. This
    function will return an instance of an object-independent (i.e., typeable) class
    derived from ObjectDataProvider.

    Returns:
        A subclass of ObjectDataProvider

    Raises:
        NotImplementedError: when receiving an object we don't know how to generated
        metadata for.
    """
    if isinstance(obj, xtgeo.RegularSurface):
        return RegularSurfaceDataProvider(obj=obj, dataio=dataio)
    if isinstance(obj, xtgeo.Polygons):
        return PolygonsDataProvider(obj=obj, dataio=dataio)
    if isinstance(obj, xtgeo.Points):
        return PointsDataProvider(obj=obj, dataio=dataio)
    if isinstance(obj, xtgeo.Cube):
        return CubeDataProvider(obj=obj, dataio=dataio)
    if isinstance(obj, xtgeo.Grid):
        return CPGridDataProvider(obj=obj, dataio=dataio)
    if isinstance(obj, xtgeo.GridProperty):
        return CPGridPropertyDataProvider(obj=obj, dataio=dataio)
    if isinstance(obj, pd.DataFrame):
        return DataFrameDataProvider(obj=obj, dataio=dataio)
    if isinstance(obj, FaultRoomSurface):
        return FaultRoomSurfaceProvider(obj=obj, dataio=dataio)
    if isinstance(obj, dict):
        return DictionaryDataProvider(obj=obj, dataio=dataio)

    from pyarrow import Table

    if isinstance(obj, Table):
        return ArrowTableDataProvider(obj=obj, dataio=dataio)

    raise NotImplementedError(f"This data type is not currently supported: {type(obj)}")


@dataclass
class DictionaryDataProvider(ObjectDataProvider):
    obj: dict

    @property
    def classname(self) -> FMUClassEnum:
        return FMUClassEnum.dictionary

    def get_spec(self) -> None:
        """Derive data.spec for dict."""

    def get_bbox(self) -> None:
        """Derive data.bbox for dict."""

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for dict."""
        return DerivedObjectDescriptor(
            subtype="JSON",
            layout="dictionary",
            efolder="dictionaries",
            fmt=(fmt := self.dataio.dict_fformat),
            extension=self._validate_get_ext(fmt, "JSON", ValidFormats().dictionary),
            table_index=None,
        )
