import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
from pydantic import BaseModel, Field, FilePath, ValidationInfo, field_validator


class Header(BaseModel):
    # name: str = Field(validation_alias="name")
    name: str = Field()

    # https://datascience.statnett.no/2020/05/11/how-we-validate-data-using-pydantic/
    # TODO: verify that using 'class Config' has the effect that other fields are
    # not allowed (catch typos, and makes it excplicit that if new features are needed
    # they must be handled here)
    # TODO: warning that class-based config is deprecated. Is it this one?
    class Config:
        extra = "forbid"

    @field_validator("name", mode="before")
    @classmethod
    def validate_header(cls, v: str) -> str:
        # Accept every string as a valid 'name'
        return v


class CoordinateSystem(BaseModel):
    name: str = Field()
    axis_name: Tuple[str, str, str] = Field()
    axis_unit: Tuple[str, str, str] = Field()
    zpositive: str = Field()
    # TODO: which other values can 'zpositive' take?

    # https://datascience.statnett.no/2020/05/11/how-we-validate-data-using-pydantic/
    # TODO: verify that using 'class Config' has the effect that other fields are
    # not allowed (catch typos, and makes it excplicit that if new features are needed
    # they must be handled here)
    class Config:
        extra = "forbid"

    @field_validator("axis_name", mode="before")
    @classmethod
    def validate_axis_name_value(cls, v: Tuple[str]) -> Tuple[str]:
        allowed_axis_names = {("X", "Y", "Z")}
        if len(v) != 3:
            raise ValueError("Invalid number of elements in 'AXIS_NAME'")
        if v not in allowed_axis_names:
            raise ValueError("Invalid 'AXIS_NAME' value")
        return v

    @field_validator("axis_unit", mode="before")
    @classmethod
    def validate_axis_unit_value(cls, v: Tuple[str]) -> Tuple[str]:
        allowed_axis_units = {("m", "m", "m")}
        if len(v) != 3:
            raise ValueError("Invalid number of elements in 'AXIS_NAME'")
        if v not in allowed_axis_units:
            raise ValueError("Invalid 'AXIS_UNIT' value")
        return v

    @field_validator("zpositive", mode="before")
    @classmethod
    def validate_z_positive_value(cls, v: str) -> str:
        allowed_zpositives = {"Depth"}
        if v not in allowed_zpositives:
            raise ValueError("Invalid 'ZPOSITIVE' value")
        return v

    @field_validator("axis_name", "axis_unit", "zpositive", mode="before")
    @classmethod
    def validate_alphanumeric(cls, v: str, info: ValidationInfo) -> str:
        if isinstance(v, str):
            # info.field_name is the name of the field being validated
            is_alphanumeric = v.replace(" ", "").isalnum()
            assert is_alphanumeric, f"{info.field_name} must be alphanumeric"
        return v


@dataclass
class TSurfFileData:
    """Data class for TSurf file data.
    TSurf is a file format for triangulations used in for example
    the GOCAD software. RMS can export the surfaces in the structural model
    in the TSurf format.
    """

    # TODO: export as simple export in fmu-dataio. See 'readers.py: faultroom'
    # and 'volumetrics' for examples.
    # Will thus have one class for reading/writing files and storing file data,
    # and another class for SUMO export.
    # The reader/writer class can thus be used independently of fmu-dataio.Export()

    # All fields are required, no more fields are allowed in this file format

    # TODO: currently you can set 'header' and 'coordinate_system' to values
    # of any type. This would result in an invalid TSurf file.
    # The TSurfFileData class is not a Pydantic BaseModel because using np.ndarray for
    # vertices and triangles is not natively supported by Pydantic. It is possible
    # to use a custom validator, but it is more complicated.
    # To validate 'header' and 'coordinate system', create __post_init__().
    # If wrong types, raise an error.
    header: Header
    coordinate_system: CoordinateSystem
    vertices: np.ndarray
    triangles: np.ndarray

    # https://datascience.statnett.no/2020/05/11/how-we-validate-data-using-pydantic/
    # TODO: verify that using 'class Config' has the effect that other fields are
    # not allowed (catch typos, and makes it excplicit that if new features are needed
    # they must be handled here)
    class Config:
        extra = "forbid"


def extract_header(lines: List[str]) -> Header:
    for line in lines:
        match = re.match(r"^(\w+):\s*(.*)$", line)
        if match and match.group(1).lower() == "name":
            name = match.group(2)
        else:
            raise ValueError("Header section is missing the 'name' field.")
    return Header(name=name)


def extract_coordinate_system(lines: List[str]) -> CoordinateSystem:
    # TODO: remove debug_print
    debug_print = False

    cs = {}
    for line in lines:
        match = re.match(r'^(\w+)\s+"(.+)"\s+"(.+)"\s+"(.+)"$', line)
        if debug_print:
            print("********* match 1: ", match)
        if match:
            # coord_sys[match.group(1).lower()] = match.groups()[1:]
            cs[match.group(1)] = match.groups()[1:]
        else:
            match = re.match(r"^(\w+)\s+(.*)$", line)
            if debug_print:
                print("********* match 2: ", match)
            if match:
                # coord_sys[match.group(1).lower()] = match.group(2)
                cs[match.group(1)] = match.group(2)

    return CoordinateSystem(
        name=cs["NAME"],
        axis_name=cs["AXIS_NAME"],
        axis_unit=cs["AXIS_UNIT"],
        zpositive=cs["ZPOSITIVE"],
    )


def parse_vertices_section(lines: List[str]) -> np.ndarray:
    """
    Parse the vertices section of a TSurf file.
    Parameters:
        lines: all lines of the vertices section
    Returns:
        numpy array of shape (num_vertices, 3) with the 3D vertex coordinates
    """

    vertices: np.ndarray = np.empty((len(lines), 3), dtype=np.float64)
    i = 0
    for line in lines:
        if line.startswith("VRTX"):
            parts = line.split()
            vertices[i] = [
                np.float64(parts[2]),
                np.float64(parts[3]),
                np.float64(parts[4]),
            ]
            i += 1
    return vertices


def parse_triangles_section(lines: List[str]) -> np.ndarray:
    """
    Parse the triangles section of a TSurf file.
    Parameters:
        lines: all lines of the triangles section
    Returns:
        numpy array of shape (num_triangles, 3) with three indices to vertices
        in the list of vertices
    """

    tris: np.ndarray = np.empty((len(lines), 3), dtype=np.int64)
    i = 0
    for line in lines:
        if line.startswith("TRGL"):
            parts = line.split()
            tris[i] = [np.int64(parts[1]), np.int64(parts[2]), np.int64(parts[3])]
            i += 1
    return tris


def read_tsurf_file(filepath: FilePath) -> TSurfFileData:
    """Read a TSurf file and return the data as a TSurfFileData object.
    TSurf is a file format for triangulations used in for example
    the GOCAD software. RMS can export the surfaces in the structural model
    in the TSurf format.
    """

    # TODO: look at 'readers.py' to handle read/write exceptions in the same way
    # (consistent user experience)

    if not filepath.exists():
        raise FileNotFoundError(f"File {filepath} does not exist.")

    with open(filepath) as file:
        lines = [line.strip() for line in file if line.strip()]

    if lines[0] != "GOCAD TSurf 1":
        raise ValueError("The first line of the file is not as expected.")

    # Currently the file is read multiple times when using lines.index()
    # TODO: parse the file line by line with if's, to avoid multiple scans of
    # a potentially large file

    # Find the HEADER section
    header_start = lines.index("HEADER {") + 1
    header_end = lines.index("}")
    header_lines = lines[header_start:header_end]
    header = extract_header(header_lines)

    # Find the coordinate system section
    coord_start = lines.index("GOCAD_ORIGINAL_COORDINATE_SYSTEM") + 1
    coord_end = lines.index("END_ORIGINAL_COORDINATE_SYSTEM")
    coord_lines = lines[coord_start:coord_end]
    coord_sys = extract_coordinate_system(coord_lines)

    indices_vrtx = [
        i for i, elem in enumerate(lines) if any(a in elem for a in ["VRTX"])
    ]
    vertices_start = indices_vrtx[0]
    vertices_end = indices_vrtx[-1] + 1
    indices_trgl = [
        i for i, elem in enumerate(lines) if any(a in elem for a in ["TRGL"])
    ]
    triangles_start = indices_trgl[0]
    triangles_end = indices_trgl[-1] + 1

    vertices_lines = lines[vertices_start:vertices_end]
    triangles_lines = lines[triangles_start:triangles_end]
    vertices = parse_vertices_section(vertices_lines)
    triangles = parse_triangles_section(triangles_lines)

    # Validate and return the parsed data
    return TSurfFileData(
        header=header,
        coordinate_system=coord_sys,
        vertices=vertices,
        triangles=triangles,
    )


def write_tsurf_file(data: TSurfFileData, filepath: Path) -> None:
    """Write a TSurf file from a TSurfFileData object.
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
        file.write("GOCAD_ORIGINAL_COORDINATE_SYSTEM\n")
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
        file.write(f"ZPOSITIVE {data.coordinate_system.zpositive}\n")
        file.write("END_ORIGINAL_COORDINATE_SYSTEM\n")
        file.write("TFACE\n")
        index = 1
        for vertex in data.vertices:
            file.write(f"VRTX {index} {vertex[0]} {vertex[1]} {vertex[2]} CNXYZ\n")
            index += 1
        for triangle in data.triangles:
            file.write(f"TRGL {triangle[0]} {triangle[1]} {triangle[2]}\n")
        file.write("END\n")


def create_TSurfFileData(data: dict) -> TSurfFileData:
    """Create a TSurfFileData object from a dictionary."""

    if not isinstance(data, dict):
        raise ValueError("Input data must be a dictionary")

    if not len(data) == 4:
        raise ValueError(
            "Input data must contain exactly "
            "4 keys: 'header', 'coordinate_system', 'vertices', 'triangles'"
        )

    if not all(
        key in data for key in ["header", "coordinate_system", "vertices", "triangles"]
    ):
        raise ValueError(
            "Input data must contain keys 'header', 'coordinate_system', "
            "'vertices', and 'triangles'"
        )

    if not isinstance(data["header"], dict):
        raise ValueError("The 'header' key must contain a dictionary")
    if not isinstance(data["coordinate_system"], dict):
        raise ValueError("The 'coordinate_system' key must contain a dictionary")
    if not isinstance(data["vertices"], np.ndarray):
        raise ValueError("The 'vertices' key must contain a numpy array")
    if not isinstance(data["triangles"], np.ndarray):
        raise ValueError("The 'triangles' key must contain a numpy array")

    header = Header(name=data["header"]["name"])
    coord_sys = CoordinateSystem(
        name=data["coordinate_system"]["name"],
        axis_name=data["coordinate_system"]["axis_name"],
        axis_unit=data["coordinate_system"]["axis_unit"],
        zpositive=data["coordinate_system"]["zpositive"],
    )
    # TODO: how does python/numpy work: will this copy the (vertices, triangles) or
    # just set a reference?
    vertices = data["vertices"]
    triangles = data["triangles"]
    return TSurfFileData(
        header=header,
        coordinate_system=coord_sys,
        vertices=vertices,
        triangles=triangles,
    )
