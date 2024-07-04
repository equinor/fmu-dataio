from __future__ import annotations

from typing import TYPE_CHECKING, Literal, MutableMapping, Union

from typing_extensions import Annotated, TypeAlias

if TYPE_CHECKING:
    import pathlib

    from pandas import DataFrame
    from pyarrow import Table
    from xtgeo.cube import Cube
    from xtgeo.grid3d import Grid, GridProperty
    from xtgeo.surface import RegularSurface
    from xtgeo.xyz import Points, Polygons

    from .readers import FaultRoomSurface

    # Local proxies due to xtgeo at the time of writing
    # not having stubs/marked itself as a typed library.
    # Ref.: https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-library-stubs-or-py-typed-marker
    class CubeProxy(Cube): ...

    class GridProxy(Grid): ...

    class GridPropertyProxy(GridProperty): ...

    class RegularSurfaceProxy(RegularSurface): ...

    class PointsProxy(Points): ...

    class PolygonsProxy(Polygons): ...

    Inferrable: TypeAlias = Annotated[
        Union[
            # XTGeo
            CubeProxy,
            GridPropertyProxy,
            GridProxy,
            PointsProxy,
            PolygonsProxy,
            RegularSurfaceProxy,
            # Others
            DataFrame,
            FaultRoomSurface,
            MutableMapping,
            Table,
            pathlib.Path,
            str,
        ],
        "Collection of 'inferrable' objects with metadata deduction capabilities",
    ]

Parameters: TypeAlias = Annotated[
    MutableMapping[str, Union[str, float, int, None, "Parameters"]],
    "Nested or flat configurations for dynamically structured parameters.",
]

Efolder: TypeAlias = Literal[
    "maps",
    "polygons",
    "points",
    "cubes",
    "grids",
    "tables",
    "dictionaries",
]

Layout: TypeAlias = Literal[
    "regular",
    "unset",
    "cornerpoint",
    "table",
    "dictionary",
    "faultroom_triangulated",
]
