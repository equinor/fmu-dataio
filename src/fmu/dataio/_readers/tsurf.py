from __future__ import annotations

import typing
import warnings
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, ClassVar

import numpy as np
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetPydanticSchema,
    ValidationError,
    field_validator,
)


class AllowedKeywordValues:
    """
    Allowed values for keywords in the TSurf file format.
    For each keyword there are multiple possible values.
    The reader does not (yet) recognise and handle all values
    that are valid in the TSurf format.
    When needed, the list can be extended.
    Note that for some of the keywords there is a short-list of allowed values
    (e.g. 'ZPOSITIVES'), other values are not allowed. The reader will issue an error
    when an invalid value is encountered.
    For other keywords (e.g. 'AXIS_NAME'), the reader will only issue a warning
    when an "uncommon" value is used.
    """

    # axis_names and axis_units: the whole tuple is specified, instead of single values
    # that can be used for each position in the tuples.
    # This is to ensure that physically meaningful relations are used.
    # For example, it makes no sense to let two elements in axis_names be equal.
    # Or to use two wildly different axis_units laterally.
    # This is quite strict and could be relaxed if needed.
    axis_names = {"xyz": ("X", "Y", "Z")}
    """XYZ are the most common axis names"""
    axis_units = {"mmm": ("m", "m", "m"), "fff": ("ft", "ft", "ft")}
    """meters is the most common unit"""
    z_positives = {"depth": "Depth", "elevation": "Elevation"}
    """Z is increasing downwards and upwards, respectively"""


class Header(BaseModel):
    """
    The header section of a TSurf file
    """

    name: str

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class CoordinateSystem(BaseModel):
    """
    The coordinate system given in a TSurf file
    """

    name: str
    axis_name: tuple[str, str, str]
    axis_unit: tuple[str, str, str]
    z_positive: str

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("axis_name", mode="before")
    @classmethod
    def validate_axis_name_value(cls, v: tuple[str]) -> tuple[str]:
        # Note: the TSurf file format specifies that the axis names are enclosed in
        # double quotes; AXIS_NAME "X" "Y" "Z". The quotes are not included in the
        # 'axis_name' field in the TSurf class, and they are removed when reading
        # the file.
        if len(v) != 3:
            raise ValueError("Invalid number of elements in 'AXIS_NAME', must be 3")
        if v not in AllowedKeywordValues.axis_names.values():
            tuples_str = ", ".join(
                [
                    "(" + ", ".join([f"'{s}'" for s in tup]) + ")"
                    for tup in AllowedKeywordValues.axis_names.values()
                ]
            )
            # The user is allowed to use any value
            warnings.warn(
                f"Uncommon 'AXIS_NAME' value: {v} "
                f"A more common value is: '{tuples_str}",
                UserWarning,
            )

        return v

    @field_validator("axis_unit", mode="before")
    @classmethod
    def validate_axis_unit_value(cls, v: tuple[str]) -> tuple[str]:
        # Note: the TSurf file format specifies that the axis names are enclosed in
        # double quotes; AXIS_UNIT "m" "m" "m". The quotes are not included in the
        # 'axis_unit' field in the TSurf data class, and they are removed when reading
        # the file.
        if len(v) != 3:
            raise ValueError("Invalid number of elements in 'AXIS_UNIT', must be 3")
        if v not in AllowedKeywordValues.axis_units.values():
            tuples_str = ", ".join(
                [
                    "(" + ", ".join([f"'{s}'" for s in tup]) + ")"
                    for tup in AllowedKeywordValues.axis_units.values()
                ]
            )
            # Different softwares may handle units differently,
            # and the available documentation is limited.
            # The user is allowed to use any value,
            # here a recommendation is provided
            warnings.warn(
                f"Uncommon 'AXIS_UNIT' value: {v} "
                f"More common values are: '{tuples_str}",
                UserWarning,
            )
        return v

    @field_validator("z_positive", mode="before")
    @classmethod
    def validate_z_positive_value(cls, v: str) -> str:
        if v not in AllowedKeywordValues.z_positives.values():
            raise ValueError(
                "Invalid 'ZPOSITIVE' value, must be one of the two following values: \n"
                + "'Depth' (Z increase downwards), or 'Elevation' (Z increase upwards)."
            )
        return v


class TSurfData(BaseModel):
    """
    Pydantic class for the data contained in a TSurf file, including reading from and
    writing to a TSurf file.
    TSurf is a file format used in for example
    the GOCAD software. RMS can export triangulated surfaces in its structural model
    in the TSurf format.
    The content of the class is validated using Pydantic.
    The class doesn't support all keywords in the TSurf format.
    The TSurf format allows specification of for example tetrahedralizations,
    polylines and other geometries, and much more.
    When unhandled keywords are present in the file, the processing is halted
    and an error message is issued. The user is expected to take action
    to fix the file.
    Documentation for the TSurf format seems to be limited, but
    here is one:
    - https://paulbourke.net/dataformats/gocad/gocad.pdf
    """

    # Allow extra fields: class doesn't support all attributes in the TSurf format,
    # and could provide feedback when recognized but yet unhandled keywords are present.
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    # Pydantic does not support Numpy's np.ndarray natively, so we let Pydantic handle
    # fields with numpy arrays as Any. Thus these fields need custom-made validators.
    # See https://docs.pydantic.dev/latest/api/types/#pydantic.types.GetPydanticSchema
    HandleAsAny: ClassVar = GetPydanticSchema(lambda _s, h: h(Any))

    header: Header
    coordinate_system: CoordinateSystem | None = Field(default=None)
    # a vertex is a 3-tuple of reals
    vertices: Annotated[np.ndarray, HandleAsAny]  # pydantic sees `vertices: Any`
    # a triangle is a 3-tuple of vertex indices in 'vertices', indexing starts from 1
    triangles: Annotated[np.ndarray, HandleAsAny]  # pydantic sees `triangles: Any`

    @field_validator("vertices", mode="before")
    @classmethod
    def validate_vertices(cls, verts: Any) -> Any:
        """
        Only data format is validated, not geometries or topology.
        'verts: Any' is what Pydantic sees
        """
        if not isinstance(verts, np.ndarray):
            raise ValueError("'vertices' must be a numpy array")
        if not verts.dtype == np.float64:
            raise ValueError("'vertices' array must be of type float64")

        # Ensure matrix shapes are OK
        if not verts.ndim == 2 or not verts.shape[1] == 3:
            raise ValueError(
                "'vertices' must be a 2D matrix of size M x 3: 'M' is the number of "
                "vertices and '3' is the number of coordinates for each vertex"
            )
        if not verts.shape[0] >= 3:
            raise ValueError("'vertices' must contain at least three vertices")
        return verts

    @field_validator("triangles", mode="before")
    @classmethod
    def validate_triangles(cls, triangs: Any) -> Any:
        """
        Only data format is validated, not geometries or topology.
        'triangs: Any' is what Pydantic sees
        """
        if not isinstance(triangs, np.ndarray):
            raise ValueError("'triangles' must be a numpy array")
        if not triangs.dtype == np.int64:
            raise ValueError("'triangles' array must be of type int64")

        # Ensure matrix shapes are OK
        if not triangs.ndim == 2 or not triangs.shape[1] == 3:
            raise ValueError(
                "'triangles' must be a 2D matrix of size M x 3: 'M' is the number of "
                "triangles and '3' is the number of vertices in each triangle"
            )
        # Note: a triangulation with zero triangles is permitted ('triangs' is empty):
        #   - could happen when modelling
        #   - such a data set defines a point cloud

        # Common mistake: file format specifies that vertices are indexed from 1 (not 0)
        if not triangs.min() >= 1:
            raise ValueError(
                "Invalid vertex index in 'triangles': indexing must start at '1'"
            )
        return triangs

    def model_post_init(self, __context: Any) -> None:
        self._validate_additional_fields()

    @staticmethod
    def _array_structure_equal(arr1: np.ndarray, arr2: np.ndarray) -> bool:
        """
        Compare two numpy arrays for equality in a shallow sense.
        Only the shape and dtype are checked, the values are not compared.
        """
        return (
            isinstance(arr1, np.ndarray)
            and isinstance(arr2, np.ndarray)
            and arr1.dtype == arr2.dtype
            and arr1.shape == arr2.shape
        )

    def __eq__(self, other: object) -> bool:
        """
        Equality operator, overrides the default implementation of a Pydantic BaseModel
        which does not have native support for numpy arrays.
        The numpy arrays are compared in a SHALLOW sense: only the shape and dtype are
        compared, not the values.
        """

        if not isinstance(other, TSurfData):
            return False

        if self is other:
            return True

        # Check optional coordinate system field
        # If one is set and the other is not, they are not considered equal
        coord_sys_equal = (self.coordinate_system is not None) == (
            other.coordinate_system is not None
        ) and (self.coordinate_system == other.coordinate_system)

        return (
            coord_sys_equal
            and self.header == other.header
            and self._array_structure_equal(self.vertices, other.vertices)
            and self._array_structure_equal(self.triangles, other.triangles)
        )

    def _validate_additional_fields(self) -> None:
        """
        If additional fields are present (with respect to required and optional fields),
        it indicates either a user error or that there are fields that are valid
        in the TSurf format but that are not (yet) handled in this class.
        """

        if self.model_extra:
            warnings.warn(
                "Unhandled fields are present, these are ignored in the processing. "
                f"The unhandled fields are: '{list(self.model_extra.keys())}'",
                UserWarning,
            )

    def num_vertices(self: TSurfData) -> int:
        return len(self.vertices)

    def num_triangles(self: TSurfData) -> int:
        return len(self.triangles)

    def bbox(self: TSurfData) -> dict[str, float]:
        """
        Return the bounding box of the triangulated surface.
        The bounding box is defined by the minimum and maximum coordinates
        in the x, y and z directions.
        """

        xmin = ymin = zmin = float("inf")
        xmax = ymax = zmax = float("-inf")
        for vertex in self.vertices:
            xcoord, ycoord, zcoord = vertex
            xmin = min(xcoord, xmin)
            ymin = min(ycoord, ymin)
            zmin = min(zcoord, zmin)
            xmax = max(xcoord, xmax)
            ymax = max(ycoord, ymax)
            zmax = max(zcoord, zmax)

        return {
            "xmin": xmin,
            "xmax": xmax,
            "ymin": ymin,
            "ymax": ymax,
            "zmin": zmin,
            "zmax": zmax,
        }


def read_tsurf_file(input: str | Path | BytesIO) -> TSurfData:
    """
    Read a TSurf file stream and create a TSurfData instance.
    TSurf is a file format for triangulations used in for example
    the GOCAD software. RMS can export the surfaces in the structural model
    in the TSurf format.
    The reader ignores commented lines (start with '#') and empty lines.
    The reader warns about keywords that are valid in the TSurf format but are not (yet)
    handled by this reader.
    The reader also warns about unknown keywords.
    """

    # Not clear if TSurf uses utf-8 encoding, but it is the safe default
    encoding = "utf-8"
    lines = []

    if isinstance(input, str):
        input = Path(input)

    if isinstance(input, Path):
        if not input.exists():
            raise FileNotFoundError(f"\nFile {input}:\nThe file does not exist.")

        if not input.is_file():
            raise FileNotFoundError(f"\nFile {input}:\nThe file is not a regular file.")

        if not input.suffix == ".ts":
            raise ValueError(
                f"\nFile {input}:\n"
                "The file is not a TSurf file. The file extension should be '.ts'."
            )

        with open(input, encoding=encoding) as stream:
            # Read and process the file line by line (more memory efficient than
            # loading entire file into memory at once)
            for line in stream:
                # remove leading/trailing whitespace and skip empty lines and comments
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith("#"):
                    lines.append(stripped_line)

    elif isinstance(input, BytesIO):
        input.seek(0)
        with input as stream:
            # The entire file is already in memory
            for stream_line in stream:
                # Decode bytes to string and strip whitespace
                stripped_line = stream_line.decode(encoding=encoding).strip()
                if stripped_line and not stripped_line.startswith("#"):
                    lines.append(stripped_line)

    else:
        raise TypeError(
            f"\nInput {input}:\nThe input must be a Path or a BytesIO object."
        )

    if not lines:
        raise ValueError(f"\nInput {input}:\nInput is empty.")

    # Check the first line
    if lines[0] != "GOCAD TSurf 1":
        raise ValueError(
            f"\n In input {input}:\n"
            "The first line indicates that this is not a valid TSurf object."
            "The first line should be 'GOCAD TSurf 1'."
        )

    parsing_header = False
    header: Header | None = None

    parsing_coord_sys = False
    coord_sys: dict[str, Any] = {}

    parsing_triangle_data = False
    v: list[list[np.float64]] = []
    t: list[list[np.int64]] = []

    for line in lines:
        if line == "GOCAD TSurf 1":
            # Skip the first line, it is already validated
            # (could be deleted from 'lines' after validation)
            pass

        # ------ Parse the header section ------
        elif line == "HEADER {":
            parsing_header = True
        elif parsing_header:
            if line.startswith("name:"):
                header = Header(name=line.split(":")[1].strip())
            elif line == "}":
                parsing_header = False
                if header is None:
                    raise ValueError(
                        f"\nIn file {input}:\n"
                        "The 'HEADER' section must exist and "
                        "is expected to have exactly one attribute: 'name'."
                    )
            else:
                raise ValueError(
                    f"\nIn file {input}:\n"
                    "The 'HEADER' section must exist and "
                    "is expected to have exactly one attribute: 'name'."
                )

        # ------ Parse the coordinate system section ------
        elif line == "GOCAD_ORIGINAL_COORDINATE_SYSTEM":
            parsing_coord_sys = True
        elif parsing_coord_sys:
            # coordinate system: fixed format
            if line.startswith("NAME"):
                coord_sys["NAME"] = line.split()[1]
            elif line.startswith("AXIS_NAME"):
                # Remove the "" that encloses each axis name
                coord_sys["AXIS_NAME"] = tuple(
                    y.replace('"', "") for y in line.split()[1:]
                )
            elif line.startswith("AXIS_UNIT"):
                # Remove the "" that encloses each axis unit
                coord_sys["AXIS_UNIT"] = tuple(
                    y.replace('"', "") for y in line.split()[1:]
                )
            elif line.startswith("ZPOSITIVE"):
                coord_sys["ZPOSITIVE"] = line.split()[1]
            elif line == "END_ORIGINAL_COORDINATE_SYSTEM":
                parsing_coord_sys = False
                if len(coord_sys) != 4:
                    raise ValueError(
                        f"\nIn file {input}:\n"
                        "Invalid 'COORDINATE_SYSTEM' section, it is "
                        "expected to have exactly four attributes:\n"
                        "'NAME', 'AXIS_NAME', 'AXIS_UNIT' and 'ZPOSITIVE'"
                    )
            else:
                raise ValueError(
                    f"\nIn file {input}:\n"
                    "Invalid 'COORDINATE_SYSTEM' section, it is "
                    "expected to have exactly four attributes:\n"
                    "'NAME', 'AXIS_NAME', 'AXIS_UNIT' and 'ZPOSITIVE'"
                )

        # ------ Parse the section with triangulated data ------
        elif line == "TFACE":
            parsing_triangle_data = True
        elif parsing_triangle_data:
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
                raise ValueError(
                    f"\nIn file {input}:\n"
                    "Invalid line in 'TFACE' section with triangulated data,\n"
                    "it is expected that all lines start with 'VRTX' or 'TRGL'.\n"
                    f"Erroneous line: '{line}'",
                )

        # ------ Handle unknown keywords ------
        else:
            # Could issue a warning instead of an error. But if this is a section that
            # continues over several lines, it is difficult to know where the
            # section ends. This may be difficult to handle.

            raise ValueError(
                f"\nIn file {input}:\n"
                "The file contains an invalid line.\n"
                "This may be either an error, or a valid TSurf keyword or attribute\n"
                "that is not (yet) handled by the file parser.\n"
                f"Erroneous line: '{line}'",
            )

    try:
        cs = CoordinateSystem(
            name=coord_sys["NAME"],
            axis_name=coord_sys["AXIS_NAME"],
            axis_unit=coord_sys["AXIS_UNIT"],
            z_positive=coord_sys["ZPOSITIVE"],
        )

        tsurfdata = TSurfData(
            header=typing.cast("Header", header),
            coordinate_system=cs,
            vertices=np.array(v),
            triangles=np.array(t),
        )

    except ValidationError as e:
        # Pydantic issues a 'ValidationError' if the data is not valid.
        # But the error message:
        #   - Does not indicate in which file the error occurred
        #   - Refers to web site that is only useful to developers
        # Here the error message is slightly improved.

        for error in e.errors():
            error_msg = (
                f"  - Section in file: '{e.title}' \n"
                f"  - Name of parameter: '{error['loc'][0]}' \n"  # Why a list?
                f"  - Input value: '{error['input']}' \n"  # Observed both str and dict
                f"  - Error message: {error['msg']} \n\n"
            )

        complete_error_msg = (
            "\n-----------------------------\n"
            f" There is {len(e.errors())} error(s) in the TSurf file: \n"
            f"'{input}' \n" + error_msg + "-----------------------------\n"
        )
        raise ValueError(complete_error_msg) from e

    return tsurfdata


def write_tsurf_to_file(data: TSurfData, output: str | Path | BytesIO) -> None:
    """
    Write a TSurfData object to file stream.
    """

    # Not clear if TSurf uses utf-8 encoding, but it is the safe default
    encoding = "utf-8"

    lines = []

    # Mandatory first line
    lines.append("GOCAD TSurf 1\n")

    lines.append("HEADER {\n")
    lines.append(f"name: {data.header.name}\n")
    lines.append("}\n")

    # Optional: coordinate system
    if data.coordinate_system:
        lines.append("GOCAD_ORIGINAL_COORDINATE_SYSTEM\n")
        lines.append(f"NAME {data.coordinate_system.name}\n")
        lines.append(
            f'AXIS_NAME "{data.coordinate_system.axis_name[0]}" '
            f'"{data.coordinate_system.axis_name[1]}" '
            f'"{data.coordinate_system.axis_name[2]}"\n'
        )
        lines.append(
            f'AXIS_UNIT "{data.coordinate_system.axis_unit[0]}" '
            f'"{data.coordinate_system.axis_unit[1]}" '
            f'"{data.coordinate_system.axis_unit[2]}"\n'
        )
        lines.append(f"ZPOSITIVE {data.coordinate_system.z_positive}\n")
        lines.append("END_ORIGINAL_COORDINATE_SYSTEM\n")

    lines.append("TFACE\n")
    for i, vertex in enumerate(data.vertices):
        lines.append(f"VRTX {i + 1} {vertex[0]} {vertex[1]} {vertex[2]} CNXYZ\n")
    for triangle in data.triangles:
        lines.append(f"TRGL {triangle[0]} {triangle[1]} {triangle[2]}\n")
    lines.append("END\n")

    if not isinstance(output, BytesIO):
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding=encoding) as file:
            file.writelines(lines)
    else:
        output.seek(0)
        output.write("".join(lines).encode(encoding))
