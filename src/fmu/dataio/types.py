import pathlib
from collections.abc import MutableMapping
from typing import Annotated, TypeAlias, Union

from pandas import DataFrame
from pyarrow import Table
from xtgeo import Cube, Grid, GridProperty, Points, Polygons, RegularSurface

from fmu.dataio._readers.tsurf import TSurfData

from ._readers.faultroom import FaultRoomSurface

ExportableData: TypeAlias = Annotated[
    Cube
    | GridProperty
    | Grid
    | Points
    | Polygons
    | RegularSurface
    | DataFrame
    | FaultRoomSurface
    | TSurfData
    | MutableMapping
    | Table
    | pathlib.Path
    | str,
    "Collection of exportable data objects with metadata deduction capabilities",
]

Parameters: TypeAlias = Annotated[
    MutableMapping[str, Union[str, float, int, None, "Parameters"]],
    "Nested or flat configurations for dynamically structured parameters.",
]
WarningTuple: TypeAlias = tuple[str, type[Warning]]
