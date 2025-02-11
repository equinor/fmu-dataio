from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from fmu.dataio._readers import tsurf as reader


def get_basic_tsurf() -> reader.TSurfData:
    """
    Create a basic TSurfData object from a dictionary.
    It contains the same data as generated in
    _create_basic_tsurf_file_as_lines().
    """

    tsurf_dict = {}
    tsurf_dict["header"] = {"name": "Fault F1"}
    tsurf_dict["coordinate_system"] = {
        "name": "Default",
        "axis_name": ("X", "Y", "Z"),
        "axis_unit": ("m", "m", "m"),
        "z_positive": "Depth",
    }
    tsurf_dict["vertices"] = np.array(
        [
            (0.1, 0.2, 0.3),
            (1.1, 1.2, 1.3),
            (2.1, 2.2, 2.3),
            (3.1, 3.2, 3.3),
        ]
    ).astype(np.float64)
    tsurf_dict["triangles"] = np.array([(1, 2, 3), (1, 2, 4)]).astype(np.int64)

    return reader.TSurfData.model_validate(tsurf_dict)


# TODO: take get_basic_tsurf() as input, then produce the lines
def get_basic_tsurf_file_as_lines() -> list[str]:
    """
    Create lines to simulate a basic TSurf file after parsing.
    Avoids the need to actually write and read a file each time when
    validating the Pydantic class 'TSurfData'.
    """

    return [
        "GOCAD TSurf 1",
        "HEADER {",
        "name: Fault F1",
        "}",
        "GOCAD_ORIGINAL_COORDINATE_SYSTEM",
        "NAME Default",
        'AXIS_NAME "X" "Y" "Z"',
        'AXIS_UNIT "m" "m" "m"',
        "ZPOSITIVE Depth",
        "END_ORIGINAL_COORDINATE_SYSTEM",
        "TFACE",
        "VRTX 1 0.1 0.2 0.3 CNXYZ",
        "VRTX 2 1.1 1.2 1.3 CNXYZ",
        "VRTX 3 2.1 2.2 2.3 CNXYZ",
        "VRTX 4 3.1 3.2 3.3 CNXYZ",
        "TRGL 1 2 3",
        "TRGL 1 2 4",
        "END",
    ]


def _validate_basic_tsurf(instance: reader.TSurfData) -> None:
    """
    Validate the basic TSurf object.
    """
    assert isinstance(instance, reader.TSurfData)
    assert instance.header.name == "Fault F1"
    assert instance.coordinate_system.name == "Default"
    assert instance.coordinate_system.axis_name == ("X", "Y", "Z")
    assert instance.coordinate_system.axis_unit == ("m", "m", "m")
    assert instance.coordinate_system.z_positive == "Depth"
    assert len(instance.vertices) == 4
    assert isinstance(instance.vertices, np.ndarray)
    assert instance.vertices.dtype == np.float64
    assert isinstance(instance.vertices[0], np.ndarray)
    assert instance.vertices[0].dtype == np.float64
    assert (instance.vertices[0] == np.array([0.1, 0.2, 0.3])).all()
    assert (instance.vertices[-1] == np.array([3.1, 3.2, 3.3])).all()
    assert len(instance.triangles) == 2
    assert isinstance(instance.triangles, np.ndarray)
    assert instance.triangles.dtype == np.int64
    assert isinstance(instance.triangles[0], np.ndarray)
    assert instance.triangles[0].dtype == np.int64
    assert (instance.triangles[0] == np.array([1, 2, 3])).all()
    assert (instance.triangles[-1] == np.array([1, 2, 4])).all()


def _insert_new_lines(lines: list[str], extra: dict) -> list[str]:
    """
    Add extra lines to the lines simulating a basic TSurf file after parsing.
    'extra' is a dictionary: {line_number: line_content}.
    Each new line will be inserted before the line number specified in 'line_number'.
    The new lines are inserted sequentially from the bottom of the file,
    so inserting new lines will not affect the numbering in 'extra'.
    """

    for position, value in sorted(extra.items(), reverse=True):
        lines.insert(position, value)

    return lines


def test_create_basic_tsurf() -> None:
    """
    Test the instantiation of a TSurfData object from a dictionary.
    """

    instance = get_basic_tsurf()
    _validate_basic_tsurf(instance)


def test_tsurf_reader_and_writer(rootpath: Path) -> None:
    """
    Test the TSurf reader and writer.
    """

    # ---------- Wrong file name suffix ----------
    instance = get_basic_tsurf()

    relpath = "tests/data/drogon/rms/output/structural/invalid_suffix.txt"
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)
    reader.write_tsurf_to_file(instance, filepath)

    with pytest.raises(
        ValueError,
        match=("is not a TSurf file."),
    ):
        reader.read_tsurf_file(filepath)

    filepath.unlink(missing_ok=True)

    # ---------- Basic TSurf file ----------
    relpath = Path("tests/data/drogon/rms/output/structural/test_read_write.ts")
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)

    reader.write_tsurf_to_file(instance, filepath)
    assert filepath.exists()

    instance = reader.read_tsurf_file(filepath)
    filepath.unlink(missing_ok=True)

    _validate_basic_tsurf(instance)

    # Test class methods
    assert instance.num_vertices() == 4
    assert instance.num_triangles() == 2


def test_tsurf_reader_comments_emptylines(rootpath: Path) -> None:
    """
    Test the reader with comments and empty lines.
    """

    relpath = Path(
        "tests/data/drogon/rms/output/structural/"
        "test_read_write_comments_emptylines_invalid_start.ts"
    )
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)

    lines = get_basic_tsurf_file_as_lines()

    # Add comments and empty lines at arbitrary positions between and inside sections.
    # The numbers indicate the line number in the file, the new lines will be inserted
    # before this line number
    comments = {
        0: "Invalid first line",
        1: "# Test comment",
        2: "# Test comment",
        4: "# Test comment",
        7: "# Test comment",
        8: "# Test comment",
        9: "# Test comment",
        11: "# Test comment",
        13: "# Test comment",
        14: "# Test comment",
        15: "# Test comment",
        16: "# Test comment",
        18: "# Test comment",
    }
    new_lines = _insert_new_lines(lines, comments)

    empty_lines = {
        1: "",
        4: "",
        10: "",
        11: "",
        17: "",
    }

    # Two first lines: comment and empty line
    new_lines_invalid_start = _insert_new_lines(new_lines, empty_lines)
    new_lines_invalid_start = [line + "\n" for line in new_lines_invalid_start]

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as file:
        file.writelines(new_lines_invalid_start)
    assert filepath.exists()

    # Ensure the file parser handles the first lines correctly
    with pytest.raises(
        ValueError,
        match=(
            "The first line of the file indicates that this is not a valid TSurf file."
        ),
    ):
        reader.read_tsurf_file(filepath)

    filepath.unlink(missing_ok=True)

    # Remove the invalid first lines
    # Continue testing the rest of the file with all its comments and empty lines
    valid_lines = new_lines_invalid_start[1:]

    relpath = (
        "tests/data/drogon/rms/output/structural/test_read_write_comments_emptylines.ts"
    )
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as file:
        file.writelines(valid_lines)
    assert filepath.exists()

    instance = reader.read_tsurf_file(filepath)
    filepath.unlink(missing_ok=True)
    _validate_basic_tsurf(instance)


def test_tsurf_reader_invalid_lines(rootpath: Path) -> None:
    """
    Test the reader with invalid lines:
    - TSurf keywords that are allowed by the file format but are
      not (yet) handled but this reader
    - plain rubbish
    """

    relpath = Path(
        "tests/data/drogon/rms/output/structural/test_read_write_invalid_lines.ts"
    )
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)

    lines_1 = get_basic_tsurf_file_as_lines()

    # Add invalid lines at arbitrary positions between and inside sections.
    invalid_lines = {
        1: "WELL_CURVE: TSurf keyword not handled by the reader",
        6: "Rubbish",
        8: "GEOLOGICAL_FEATURE: TSurf keyword not handled by the reader",
        14: "Rubbish",
    }
    lines_2 = _insert_new_lines(lines_1, invalid_lines)
    lines_3 = [line + "\n" for line in lines_2]

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as file:
        file.writelines(lines_3)
    assert filepath.exists()

    with pytest.raises(
        ValueError,
        match="This may be an error or a valid TSurf content that is not handled",
    ):
        reader.read_tsurf_file(filepath)

    filepath.unlink(missing_ok=True)


def test_tsurf_reader_RMS_file(rootpath: Path) -> None:
    """
    Test the reader with a TSurf file generated by RMS.
    """

    relpath = Path("tests/data/drogon/rms/output/structural/F5.ts")
    filepath = rootpath / relpath

    instance = reader.read_tsurf_file(filepath)

    assert instance.header.name == "F5"
    assert instance.coordinate_system.name == "Default"
    assert (
        instance.coordinate_system.axis_name
        == reader.AllowedKeywordValues.axis_names[0]
    )
    assert (
        instance.coordinate_system.axis_unit
        == reader.AllowedKeywordValues.axis_units[0]
    )
    assert (
        instance.coordinate_system.z_positive
        == reader.AllowedKeywordValues.z_positives[0]
    )
    assert len(instance.vertices) == 44
    assert (
        instance.vertices[0] == np.array([459621.051270, 5934843.011475, 1685.590820])
    ).all()
    assert (
        instance.vertices[-1] == np.array([459651.376465, 5936259.713867, 1721.204224])
    ).all()
    assert len(instance.triangles) == 65
    assert (instance.triangles[0] == np.array([24, 25, 28])).all()
    assert (instance.triangles[-1] == np.array([43, 8, 44])).all()


def test_parsing_file_with_errors(rootpath: Path) -> None:
    """
    Test the file parser with a TSurf file with content that should produce
    errors.
    """

    relpath = Path(
        "tests/data/drogon/rms/output/structural/basic_tsurf_file_with_errors.ts"
    )
    filepath = rootpath / relpath

    with pytest.raises(ValueError, match="Invalid 'ZPOSITIVE' value"):
        reader.read_tsurf_file(filepath)


def test_parsing_file_with_warnings(rootpath: Path) -> None:
    """
    Test the file parser with a TSurf file with content that should produce
    warnings.
    """

    relpath = Path(
        "tests/data/drogon/rms/output/structural/basic_tsurf_file_with_warnings.ts"
    )
    filepath = rootpath / relpath

    with pytest.warns(UserWarning, match="Uncommon 'AXIS_UNIT' value"):
        reader.read_tsurf_file(filepath)


def test_validation_header():
    """Test the validation of the TSurf header."""

    ###############
    # Instantiation
    ###############

    header = reader.Header(name="Fault F1")
    assert header.name == "Fault F1"
    # Update
    header.name = "Fault F2"
    assert header.name == "Fault F2"

    # Empty header
    with pytest.raises(ValidationError, match="Field required"):
        header = reader.Header()

    # Pydantic has keyword only constructors, positional arguments are not allowed
    with pytest.raises(TypeError, match="takes 1 positional argument but 2 were given"):
        header = reader.Header("Positional_argument_not_allowed")

    # Invalid input parameter type
    with pytest.raises(ValidationError, match="validation error for Header"):
        header = reader.Header(name=73)

    # Invalid fields in header
    with pytest.raises(ValidationError, match="validation error for Header"):
        header = reader.Header(name="Fault F1", extra_field="invalid")

    ########################
    # Modify existing object
    ########################

    # Invalid input parameter type
    with pytest.raises(ValidationError, match="validation error for Header"):
        header = reader.Header(name=73)

    # Invalid input parameter type
    with pytest.raises(ValidationError, match="validation error for Header"):
        header = reader.Header(name=None)


def test_validation_coordinate_system():
    """
    Test the validation of the TSurf coordinate system.
    """

    ###############
    # Instantiation
    ###############

    coord_sys = reader.CoordinateSystem(
        name="Default",
        axis_name=("X", "Y", "Z"),
        axis_unit=("m", "m", "m"),
        z_positive="Depth",
    )
    assert coord_sys.name == "Default"
    assert coord_sys.axis_name == ("X", "Y", "Z")
    assert coord_sys.axis_unit == ("m", "m", "m")
    assert coord_sys.z_positive == "Depth"

    # Missing field
    with pytest.raises(ValidationError, match="validation error for CoordinateSystem"):
        coord_sys = reader.CoordinateSystem(
            # Missing name
            axis_name=("X", "Y", "Z"),
            axis_unit=("m", "m", "m"),
            z_positive="Depth",
        )

    # Invalid field (axis_name only to elements)
    with pytest.raises(
        ValidationError, match="Invalid number of elements in 'AXIS_NAME', must be 3"
    ):
        coord_sys = reader.CoordinateSystem(
            name="Default",
            axis_name=("X", "Y"),
            axis_unit=("m", "m", "m"),
            z_positive="Depth",
        )

    # Invalid field (axis_unit has element with invalid unit)
    with pytest.warns(UserWarning, match="Uncommon 'AXIS_UNIT' value:"):
        coord_sys = reader.CoordinateSystem(
            name="Default",
            axis_name=("X", "Y", "Z"),
            axis_unit=("m", "nm", "m"),
            z_positive="Depth",
        )

    # Invalid value type in field (axis_unit)
    with pytest.raises(
        ValidationError, match="Invalid number of elements in 'AXIS_UNIT'"
    ):
        coord_sys = reader.CoordinateSystem(
            name="Default",
            axis_name=("X", "Y", "Z"),
            axis_unit=np.ndarray([1, 2, 3]),
            z_positive="Depth",
        )

    # Invalid value type in field (z_positive)
    with pytest.raises(ValidationError, match="Invalid 'ZPOSITIVE' value"):
        coord_sys = reader.CoordinateSystem(
            name="Default",
            axis_name=("X", "Y", "Z"),
            axis_unit=("m", "m", "m"),
            z_positive=56,
        )

    ########################
    # Modify existing object
    ########################

    # Update
    valid_name = "Another name"
    coord_sys.name = valid_name
    assert coord_sys.name == valid_name

    # Invalid type
    invalid_name_type = 6.4
    with pytest.raises(ValidationError, match="Input should be a valid string"):
        coord_sys.name = invalid_name_type

    # Invalid value (2 elements instead of 3)
    uncommon_axis_name = ("X", "Y")
    with pytest.raises(
        ValidationError, match="Invalid number of elements in 'AXIS_NAME', must be 3"
    ):
        coord_sys.axis_name = uncommon_axis_name

    # Uncommon value
    uncommon_axis_name = ("Y", "Z", "X")
    with pytest.warns(
        UserWarning,
        match="Uncommon 'AXIS_NAME' value:",
    ):
        coord_sys.axis_name = uncommon_axis_name

    # Uncommon value
    uncommon_axis_unit = ("m", "m", "km")
    with pytest.warns(
        UserWarning,
        match="Uncommon 'AXIS_UNIT' value:",
    ):
        coord_sys.axis_unit = uncommon_axis_unit

    # Invalid value
    invalid_z_positive = "Top"
    with pytest.raises(ValidationError, match="Invalid 'ZPOSITIVE' value"):
        coord_sys.z_positive = invalid_z_positive

    # Invalid type
    invalid_z_positive_type = reader.Header(name="Fault F1")
    with pytest.raises(ValidationError, match="Invalid 'ZPOSITIVE' value"):
        coord_sys.z_positive = invalid_z_positive_type


def test_validation_tsurf_instantiation():
    """
    Test the validation of the TSurf data when creating new objects.
    """

    header = reader.Header(name="Fault F1")
    coord_sys = reader.CoordinateSystem(
        name="Default",
        axis_name=reader.AllowedKeywordValues.axis_names[0],
        axis_unit=reader.AllowedKeywordValues.axis_units[0],
        z_positive=reader.AllowedKeywordValues.z_positives[0],
    )
    vertices = np.array(
        [
            (0.1, 0.2, 0.3),
            (1.1, 1.2, 1.3),
            (2.1, 2.2, 2.3),
            (3.1, 3.2, 3.3),
        ]
    ).astype(np.float64)
    triangles = np.array([(1, 2, 3), (1, 2, 4)]).astype(np.int64)

    instance = reader.TSurfData(
        header=header,
        coordinate_system=coord_sys,
        vertices=vertices,
        triangles=triangles,
    )

    assert (
        instance.coordinate_system.axis_name
        == reader.AllowedKeywordValues.axis_names[0]
    )

    #########################
    # Validate set of fields
    #########################

    # Optional field missing (coordinate_system)
    assert reader.TSurfData(header=header, vertices=vertices, triangles=triangles)

    # Required field missing AND invalid key
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        reader.TSurfData(
            header=reader.Header(invalid_key=""), vertices=vertices, triangles=triangles
        )

    # Required field missing (triangles)
    with pytest.raises(ValidationError, match="Field required"):
        reader.TSurfData(header=header, vertices=vertices)

    with pytest.raises(ValidationError, match="header"):
        reader.TSurfData(
            header="invalid",
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles=triangles,
        )

    # Extra field: ensure user is informed
    with pytest.warns(UserWarning, match="Unhandled fields are present"):
        reader.TSurfData(
            header=header, vertices=vertices, extra_field="invalid", triangles=triangles
        )

    #########################
    # Validate vertices field
    #########################
    with pytest.raises(ValidationError, match="'vertices' must be a numpy array"):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices="invalid",
            triangles=triangles,
        )

    with pytest.raises(
        ValidationError, match="'vertices' must contain at least three vertices"
    ):
        verts = np.array(
            [
                (0.1, 0.2, 0.3),
            ]
        ).astype(np.float64)
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=verts,
            triangles=triangles,
        )

    with pytest.raises(
        ValidationError, match="'vertices' must contain at least three vertices"
    ):
        verts = np.array(
            [
                (0.1, 0.2, 0.3),
                (1.1, 1.2, 1.3),
            ]
        ).astype(np.float64)
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=verts,
            triangles=triangles,
        )

    with pytest.raises(
        ValidationError, match="'vertices' array must be of type float64"
    ):
        verts = np.array(
            [
                (0.1, 0.2, 0.3),
                (1.1, 1.2, 1.3),
            ]
        ).astype(np.float32)
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=verts,
            triangles=triangles,
        )

    ##########################
    # Validate triangles field
    ##########################
    with pytest.raises(ValidationError, match="'triangles' must be a numpy array"):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles="invalid",
        )

    with pytest.raises(
        ValidationError, match="'triangles' must be a 2D matrix of size M x 3:"
    ):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles=np.array([(1, 2)]),  # 1 x 3 matrix
        )

    with pytest.raises(
        ValidationError, match="'triangles' array must be of type int64"
    ):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles=np.array([("invalid", 2, 3)]),
        )

    with pytest.raises(
        ValidationError, match="'triangles' must be a 2D matrix of size M x 3:"
    ):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles=np.empty(0, dtype=np.int64),
        )

    #############################
    # Validate triangulation data
    #############################

    # A few basic checks to avoid common mistakes

    # Vertex index smaller than 1 in 'triangles'
    # Not allowed as indexing starts at 1 in the TSurf format
    with pytest.raises(
        ValidationError,
        match="Invalid vertex index in 'triangles': indexing must start at '1'",
    ):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles=np.array([(1, 0, 1)]),
        )


def test_validation_tsurf_data_modification():
    """
    Test the validation of the TSurf data when modifying an existing object.
    """

    instance1 = get_basic_tsurf()

    # Valid type
    instance1.header = reader.Header(name="Fault F2")

    # Invalid type
    with pytest.raises(ValidationError, match="Invalid header"):
        instance1.header = "Invalid header"

    # Optional field, so OK to set to None
    instance1.coordinate_system = None

    instance1 = get_basic_tsurf()
    with pytest.warns(UserWarning, match="Uncommon 'AXIS_NAME' value:"):
        instance1.coordinate_system.axis_name = ("X", "Y", "ZZZZZZ")

    # Change vertices
    instance1 = get_basic_tsurf()
    # Type and structure are valid, should not raise an error
    instance1.vertices = np.array(
        [
            (5.1, 5.2, 5.3),
            (6.1, 6.2, 6.3),
            (7.1, 7.2, 7.3),
        ]
    ).astype(np.float64)

    # Invalid type
    with pytest.raises(ValidationError, match="'vertices' must be a numpy array"):
        instance1.vertices = "invalid_type"

    # Invalid structure
    with pytest.raises(
        ValidationError, match="'vertices' must be a 2D matrix of size M x 3:"
    ):
        instance1.vertices = np.zeros((2, 2), dtype=np.float64)

    # Invalid numpy type
    with pytest.raises(
        ValidationError, match="'vertices' array must be of type float64"
    ):
        instance1.vertices = np.array(
            [
                (5.1, 5.2, 5.3),
                (6.1, 6.2, 6.3),
                (7.1, 7.2, 7.3),
            ]
        ).astype(np.float32)

    # Change triangles
    instance1 = get_basic_tsurf()
    # Type and structure are valid, should not raise an error
    instance1.triangles = np.array(
        [
            (5, 7, 2),
        ]
    ).astype(np.int64)

    # Invalid type
    with pytest.raises(ValidationError, match="'triangles' must be a numpy array"):
        instance1.triangles = 54

    # Invalid structure
    with pytest.raises(
        ValidationError, match="'triangles' must be a 2D matrix of size M x 3:"
    ):
        instance1.triangles = np.zeros((2, 2), dtype=np.int64)

    # Invalid numpy type
    with pytest.raises(
        ValidationError, match="'triangles' array must be of type int64"
    ):
        instance1.triangles = np.array(
            [
                (5, 7, 2),
            ]
        ).astype(np.int8)


def test_tsurf_data_equality():
    """
    Test the equality of TSurfData objects.
    For the triangulated data, only the structure of the numpy arrays is considered,
    not the values.
    """

    # Create two identical instances
    instance1 = get_basic_tsurf()
    instance2 = get_basic_tsurf()

    # Test equality operator
    assert instance1 == instance2

    # instance1 and instance3 refer to the same object
    instance3 = instance1
    assert instance1 == instance3

    # Change header
    instance2 = get_basic_tsurf()
    instance2.header.name = "Fault F2"
    assert instance1 != instance2

    # Coordinate system exists in one but not in the other
    # Should throw as the coordinate systems are not equal,
    # even though the field is optional
    instance2 = get_basic_tsurf()
    instance2.coordinate_system = None
    assert instance1 != instance2

    # Change vertex value
    # The equality check does not consider the values, only the structure,
    # so this should pass
    instance2 = get_basic_tsurf()
    instance2.vertices[0, 2] = np.nan
    assert instance1 == instance2

    # Change triangle index value
    # The equality check does not consider the values, only the structure,
    # so this should pass
    instance2 = get_basic_tsurf()
    instance2.triangles[0, 2] = instance1.triangles[0, 2] + 1
    assert instance1 == instance2

    instance2 = get_basic_tsurf()
    # Remove the first triangle, to ensure that the matrix dimensions are different
    instance2.triangles = instance1.triangles[:-1]
    assert instance1 != instance2

    # Extra fields
    instance2 = get_basic_tsurf()
    instance2.extra_field = "invalid"
    # Extra fields are allowed, but since they are ignored by the class
    # the instances are considered equal
    assert instance1 == instance2
