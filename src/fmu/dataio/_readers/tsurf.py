from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Optional, Tuple, Union

import numpy as np
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    GetPydanticSchema,
    field_validator,
)
from typing_extensions import Annotated


class Header(BaseModel):
    """Data class for the header section of a TSurf file."""

    name: str = Field()

    model_config = ConfigDict(extra="forbid")



class CoordinateSystem(BaseModel):
    """
    The coordinate system of a TSurf file
    """

    name: str = Field()
    axis_name: Union[Tuple[()], Tuple[str, str, str]] = Field()
    axis_unit: Union[Tuple[()], Tuple[str, str, str]] = Field()
    z_positive: str = Field()
    # TODO: which other values can axis_name and axis_unit take?

    model_config = ConfigDict(extra="forbid")

    # TODO: what is 'root_validator', can it be used here?
    # Possibly to check the validity of the complete instantiation?

    @field_validator("axis_name", mode="before")
    @classmethod
    def validate_axis_name_value(cls, v: Tuple[str]) -> Tuple[str]:
        """
        Note: the TSurf file format specifies that the axis names are enclosed in
        double quotes; AXIS_NAME "X" "Y" "Z". The quotes are not included in the
        'AXIS_NAME' field in the TSurf file, and they are removed when reading the file.
        """
        allowed_axis_names = {("X", "Y", "Z")}
        if len(v) != 3:
            # Catch a typical mistake
            raise ValueError("Invalid number of elements in 'AXIS_NAME', must be 3")
        if v not in allowed_axis_names:
            raise ValueError(
                "Invalid 'AXIS_NAME' value, must be one of the following sets: ",
                allowed_axis_names,
            )
            # TODO: print the set of allowed values
        return v

    @field_validator("axis_unit", mode="before")
    @classmethod
    def validate_axis_unit_value(cls, v: Tuple[str]) -> Tuple[str]:
        """
        Note: the TSurf file format specifies that the axis names are enclosed in
        double quotes; AXIS_UNIT "m" "m" "m". The quotes are not included in the
        'AXIS_UNIT' field in the TSurf file, and they are removed when reading the file.
        """
        allowed_axis_units = {("m", "m", "m")}
        if len(v) != 3:
            # Catch a typical mistake
            raise ValueError("Invalid number of elements in 'AXIS_NAME', must be 3")
        if v not in allowed_axis_units:
            raise ValueError(
                "Invalid 'AXIS_UNIT' value, must be one of the following set(s): ",
                allowed_axis_units,
            )
            # TODO: print the set of allowed values
        return v

    @field_validator("z_positive", mode="before")
    @classmethod
    def validate_z_positive_value(cls, v: str) -> str:
        # Depth (Z is increasing downwards), Elevation (Z is increasing upwards)
        allowed_zpositives = {"Depth", "Elevation"}
        if v not in allowed_zpositives:
            raise ValueError(
                "Invalid 'ZPOSITIVE' value, must be 'Depth' or 'Elevation'"
            )
        return v


# Pydantic does not support np.ndarray natively, so we let Pydantic handle fields
# with numpy arrays as Any. The fields need custom-made validators.
# See https://docs.pydantic.dev/latest/api/types/#pydantic.types.GetPydanticSchema
HandleAsAny = GetPydanticSchema(lambda _s, h: h(Any))


class TSurfData(BaseModel):
    """
    Data class for TSurf file data.
    TSurf is a file format for triangulations used in for example
    the GOCAD software. RMS can export the surfaces in the structural model
    in the TSurf format.
    Documentation for the TSurf format is limited.
    Here are a few sources:
    - https://paulbourke.net/dataformats/gocad/gocad.pdf
    """

    # TODO: field validation
    # TSurfData is not a Pydantic BaseModel because Pydantic does
    # not support np.ndarray natively.
    # Thus the 'header' and 'coordinate_system' fields are not verified by Pydantic,
    # while the numpy arrays are verified by the dataclass.
    # Question: is it important that the class is valid when doing the export?
    # E.g. if a user changes a field of an existing object to something invalid,
    # should he fix it himself when the export fails?
    # from future import Annotations: is this relevant here?
    # Alternatives:
    # - https://docs.pydantic.dev/latest/concepts/dataclasses
    #   - a normal dataclass with some extra Pydantic functionality
    # - Use Sindre's suggestion, then do custom validation of the numpy arrays:
    #   - validate() in __post_init__() and before export (in the export function)
    # - use a Pydantic BaseModel and convert the numpy arrays to lists
    #   - may be slow for large arrays
    # - use a Pydantic BaseModel and write custom validators for the numpy arrays
    #   (suggested by CoPilot)
    # - use a Pydantic BaseModel and write a custom validator for the whole object
    #   (suggested by CoPilot)
    # - use numpydantic, pydantic_numpy, or another library that supports numpy arrays

    # Allow extra fields as class doesn't support all attributes in the TSurf format
    model_config = ConfigDict(extra="allow")

    header: Header = Field()
    coordinate_system: Optional[CoordinateSystem] = Field(default=None)
    # a vertex is a 3-tuple of reals
    vertices: Annotated[np.ndarray, HandleAsAny]  # pydantic sees `vertices: Any`
    # a triangle is a 3-tuple of vertex indices in 'vertices'
    triangles: Annotated[np.ndarray, HandleAsAny]  # pydantic sees `triangles: Any`

    def model_post_init(self, __context: Any) -> None:
        self._validate_fields()
        self._validate_triangulation_data()

    def __eq__(self, other: object) -> bool:
        """
        Equality operator, overrides the default implementation of a Pydantic BaseModel
        which does not have native support for numpy arrays.
        """

        if not isinstance(other, TSurfData):
            return False

        return (
            self.header == other.header
            and self.coordinate_system == other.coordinate_system
            # TODO: check if this array check is a shallow comparison (shape, type,
            # ...) or if it also checks the values. Value checking could be
            # time-consuming and should be avoided.
            # If only  a shallow comparison, should rename function to e.g.
            # _eq_shallow, _shallow_compare or similar
            and np.array_equal(self.vertices, other.vertices)
            and np.array_equal(self.triangles, other.triangles)
        )

    def _validate_fields(self) -> None:
        """
        If additional fields are present compared to requied and optional fields,
        it may indicate that there are fields that are valid in the TSurf format
        but that are not yet handled in this class yet.
        """

        if self.model_extra:
            warnings.warn(
                "Unhandled fields are present, these are ignored in the SUMO upload. "
                f"The unhandled fields are: '{list(self.model_extra.keys())}'",
                UserWarning,
            )

    def _validate_triangulation_data(self) -> None:
        """
        Verify that the data is a valid set of vertices and triangles, respectively.
        The extra validation is needed as Pydantic does not support numpy arrays.
        Only data format is validated, not geometries or topology.
        """
        if not isinstance(self.vertices, np.ndarray):
            raise ValueError("'vertices' must be a numpy array")
        if not isinstance(self.triangles, np.ndarray):
            raise ValueError("'triangles' must be a numpy array")

        if not self.vertices.dtype == np.float64:
            raise ValueError("'vertices' must be of type float64")
        if not self.triangles.dtype == np.int64:
            raise ValueError("'triangles' must be of type int64")

        # Ensure matrix shapes are OK
        if not self.vertices.ndim == 2 or not self.vertices.shape[1] == 3:
            raise ValueError(
                "'vertices' must be a 2D matrix of size M x 3: 'M' is the number of "
                "vertices and '3' is the number of coordinates for each vertex"
            )
        if not self.triangles.ndim == 2 or not self.triangles.shape[1] == 3:
            raise ValueError(
                "'triangles' must be a 2D matrix of size M x 3: 'M' is the number of "
                "triangles and '3' is the number of vertices in each triangle"
            )
        if not self.vertices.shape[0] >= 3:
            raise ValueError("'vertices' must contain at least three vertices")

        # Note: a triangulation with zero triangles is permitted:
        # could happen when modelling

        # Common mistake: file format specifies that vertices are indexed from 1 (not 0)
        if not self.triangles.min() >= 1:
            raise ValueError("Invalid vertex index in 'triangles': smaller than '1'")

    # TODO: have a look at readers.FaultRoomSurface
    # May use __post_init__ etc.
    # But probably not necessary when using Pydantic


def num_vertices(self: TSurfData) -> int:
    return len(self.vertices)


def num_triangles(self: TSurfData) -> int:
    return len(self.triangles)


def read_tsurf_file(filepath: FilePath) -> TSurfData:
    """
    Read a TSurf file and return the data as a TSurfData object.
    TSurf is a file format for triangulations used in for example
    the GOCAD software. RMS can export the surfaces in the structural model
    in the TSurf format.
    The reader should to some degree handle entries that are not
    supported by TSurfData and provide meaningful warnings,
    but no guarantees are given in such cases.
    """

    # TODO: look at 'readers.py' to handle read/write exceptions in the same way
    # (consistent user experience)

    if not filepath.exists():
        raise FileNotFoundError(f"File {filepath} does not exist.")

    with open(filepath) as file:
        lines = [
            # remove leading/trailing whitespace and skip empty lines and comments
            line.strip()
            for line in file
            if line.strip() and not line.startswith("#")
        ]

    if lines[0] != "GOCAD TSurf 1":
        raise ValueError("The first line of the file is not as expected.")

    # TODO: handle lines with keywords that are allowed according to the
    # GOCAD TSurf format, but are not handled by the parser

    parsing_header = False
    header = {}

    parsing_coord_sys = False
    coord_sys = {}

    parsing_triangle_data = False
    v = []
    t = []

    for line in lines:
        # Skip the first line, it is already validated
        if line == "GOCAD TSurf 1":
            continue

        # Parse the header section
        if line == "HEADER {":
            parsing_header = True
            continue
        if parsing_header:
            # TODO: write test
            if line.startswith("name:"):
                header = Header(name=line.split(":")[1].strip())
            elif line == "}":
                parsing_header = False
                if header is None:
                    # TODO: write test
                    raise ValueError(
                        "In file {filepath}: The HEADER section is expected to have a "
                        "single attribute: 'name'"
                    )
            else:
                # TODO: write test
                raise ValueError(
                    "In file {filepath}: The HEADER section is expected to have a "
                    "single attribute: 'name'"
                )
            continue

        # Parse the coordinate system section
        if line == "GOCAD_ORIGINAL_COORDINATE_SYSTEM":
            parsing_coord_sys = True
            continue
        if parsing_coord_sys:
            # coordinate system: fixed format
            if line.startswith("NAME"):
                coord_sys["NAME"] = line.split()[1]
            elif line.startswith("AXIS_NAME"):
                # Remove the "" that encloses each axis name
                t1 = [y.replace('"', "") for y in line.split()[1:]]
                coord_sys["AXIS_NAME"] = tuple(t1)
                #coord_sys["AXIS_NAME"] = tuple(
                #    y.replace('"', "") for y in line.split()[1:]
                #)
            elif line.startswith("AXIS_UNIT"):
                # Remove the "" that encloses each axis name
                coord_sys["AXIS_UNIT"] = tuple(
                    y.replace('"', "") for y in line.split()[1:]
                )
            elif line.startswith("ZPOSITIVE"):
                coord_sys["ZPOSITIVE"] = line.split()[1]
            elif line == "END_ORIGINAL_COORDINATE_SYSTEM":
                parsing_coord_sys = False
                # TODO: check if all values are set (check for None all)
                if len(coord_sys) != 4:
                    # TODO: write test
                    raise ValueError(
                        "In {filepath}: Invalid COORDINATE_SYSTEM section, it is "
                        "expected to have exactly four attributes:  'NAME', "
                        "'AXIS_NAME', 'AXIS_UNIT' and 'ZPOSITIVE'"
                    )
            else:
                # TODO: write test
                raise ValueError(
                    "In file {filepath}: Invalid COORDINATE_SYSTEM section, it is "
                    "expected to have exactly four attributes:  'NAME', "
                    "'AXIS_NAME', 'AXIS_UNIT' and 'ZPOSITIVE'"
                )
            continue

        # Parse the section with triangulated data
        if line == "TFACE":
            parsing_triangle_data = True
            continue
        if parsing_triangle_data:
            parts = line.split()
            if parts[0] == "VRTX":
                # simply ignore the vertex number (parts[1]) and the 'CNXYZ' (parts[5])
                v.append(
                    [np.float64(parts[2]), np.float64(parts[3]), np.float64(parts[4])]
                )
            elif parts[0] == "TRGL":
                t.append([np.int64(parts[1]), np.int64(parts[2]), np.int64(parts[3])])
            elif line == "END":
                parsing_triangle_data = False
            else:
                # TODO: write test
                raise ValueError(
                    "In file {filepath}: invalid section with triangulated data, "
                    "expect that all lines start with 'VRTX' or 'TRGL'"
                )
            continue

    # Validate and return the parsed data
    cs = CoordinateSystem(
        name=coord_sys["NAME"],
        axis_name=coord_sys["AXIS_NAME"],
        axis_unit=coord_sys["AXIS_UNIT"],
        z_positive=coord_sys["ZPOSITIVE"],
    )
    return TSurfData(
        header=header,
        coordinate_system=cs,
        vertices=np.array(v),
        triangles=np.array(t),
    )


def write_tsurf_file(data: TSurfData, filepath: Path) -> None:
    """Write a TSurf file from a TSurfData object.
    TSurf is a file format for triangulations used in for example
    the GOCAD software. RMS can export the surfaces in the structural model
    in the TSurf format.
    """

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as file:
        file.write("GOCAD TSurf 1\n")
        file.write("HEADER {\n")
        file.write(f"name: {data.header.name}\n")
        file.write("}\n")

        if data.coordinate_system:
            file.write("GOCAD_ORIGINAL_COORDINATE_SYSTEM\n")
            # TODO: coordinate_system is optional
            # the consumer may choose to make his own, but not required???
            # Just check if it exists or not
            file.write(f"NAME {data.coordinate_system.name}\n")
            file.write(
                f'AXIS_NAME "{data.coordinate_system.axis_name[0]}" '
                f'"{data.coordinate_system.axis_name[1]}" '
                f'"{data.coordinate_system.axis_name[2]}"\n'
            )
            file.write(
                f'AXIS_UNIT "{data.coordinate_system.axis_unit[0]}" '
                f'"{data.coordinate_system.axis_unit[1]}" '
                f'"{data.coordinate_system.axis_unit[2]}"\n'
            )
            file.write(f"ZPOSITIVE {data.coordinate_system.z_positive}\n")
            file.write("END_ORIGINAL_COORDINATE_SYSTEM\n")

        file.write("TFACE\n")
        v_idx = 1
        for vertex in data.vertices:
            file.write(f"VRTX {v_idx} {vertex[0]} {vertex[1]} {vertex[2]} CNXYZ\n")
            v_idx += 1
        for triangle in data.triangles:
            file.write(f"TRGL {triangle[0]} {triangle[1]} {triangle[2]}\n")
        file.write("END\n")


def create_tsurf_filedata(data: dict) -> TSurfData:
    """Create a TSurfData object from a dictionary."""

    # TODO: error checking on the input dictionary isn't necessary, as the
    # TSurfData object will do this anyway

    # TODO: this entire function is unnecessary, as the TSurfData object
    # can possibly be created directly from the dictionary?
    # Check with somebody

    if not isinstance(data, dict):
        raise ValueError("Input data must be a dictionary")

    if not len(data) == 4:
        raise ValueError("Input dict must contain exactly 4 keys")

    if not all(
        # TODO: coordinate_system is optional
        key in data
        for key in ["header", "coordinate_system", "vertices", "triangles"]
    ):
        raise ValueError(
            "Input data must contain keys 'header', 'coordinate_system', "
            "'vertices', and 'triangles'"
        )

    if not isinstance(data["header"], dict):
        raise ValueError("The 'header' key must have a dictionary as value")
    if not isinstance(data["coordinate_system"], dict):
        raise ValueError("The 'coordinate_system' key must have a dictionary as value")
    if not isinstance(data["vertices"], np.ndarray):
        raise ValueError("The 'vertices' key must have a numpy array as value")
    if not isinstance(data["triangles"], np.ndarray):
        raise ValueError("The 'triangles' key must have a numpy array as value")

    # TODO: all the above checks the dict: but should check the creation of
    # the TSurfData object

    header = Header(name=data["header"]["name"])
    coord_sys = CoordinateSystem(
        name=data["coordinate_system"]["name"],
        axis_name=data["coordinate_system"]["axis_name"],
        axis_unit=data["coordinate_system"]["axis_unit"],
        z_positive=data["coordinate_system"]["zpositive"],
    )
    # TODO: how does python/numpy work: will this copy the (vertices, triangles) or
    # just set a reference?
    vertices = data["vertices"]
    triangles = data["triangles"]
    return TSurfData(
        header=header,
        coordinate_system=coord_sys,
        vertices=vertices,
        triangles=triangles,
    )
