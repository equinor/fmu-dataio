from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from fmu.dataio._readers import tsurf as reader


def _create_basic_tsurf_file_as_lines() -> list[str]:
    """
    Create lines for a basic TSurf file for testing purposes.
    Contains only data that are supported by the reader.
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
    Validate the data a basic TSurf object as generated from
    _create_basic_tsurf_file_as_lines().
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
    Add extra data to the TSurf file for testing purposes.
    'extra' is a dictionary: {line_number: line_content}.
    The new lines will be inserted BEFORE the line number specified in 'line_number'.
    Note that line_number refers to the line numbers in 'lines', so
    inserting new lines will not affect this numbering.
    The new lines are inserted sequentially.
    """

    new_lines = lines.copy()

    # Insert values from 'extra' into list a at the specified positions
    for position, value in sorted(extra.items(), reverse=True):
        new_lines.insert(position, value)

    # TODO: remove the following if the above works
    # new_lines = []
    # for line_number, line_content in extra.items():
    #     new_lines.append(line_content)
    #     lines.insert(line_number, line_content)

    return new_lines


# TODO: WELL_CURVE etc
def _create_hardcoded_file_unsupported_entries(filepath: Path) -> None:
    """
    Create a hardcoded TSurf file for testing purposes.
    The file contains entries that exist in the TSurf format but are
    not supported by the reader.
    The reader should ignore (and skip) such entries without failing.
    """

    with open(filepath, "w") as file:
        file.write("""GOCAD TSurf 1
HEADER {
name: Fault F1
}
GOCAD_ORIGINAL_COORDINATE_SYSTEM
NAME Default
AXIS_NAME "X" "Y" "Z"
AXIS_UNIT "m" "m" "m"
ZPOSITIVE Depth
END_ORIGINAL_COORDINATE_SYSTEM
#  Unsupported single line entry GEOLOGICAL_TYPE (start)
GEOLOGICAL_TYPE unconformity
#  Unsupported single line entry GEOLOGICAL_TYPE (end)
#  Unsupported multi line entry WELL_CURVE (start)
WELL_CURVE
# ... more lines describing WELL_CURVE, but would result in undefined behaviour
END
#  Unsupported multi line entry WELL_CURVE (end)
TFACE
VRTX 1 0.1 0.2 0.3 CNXYZ
VRTX 2 1.1 1.2 1.3 CNXYZ
VRTX 3 2.1 2.2 2.3 CNXYZ
VRTX 4 3.1 3.2 3.3 CNXYZ
TRGL 1 2 3
TRGL 1 2 4
END
""")


def _create_basic_tsurf_from_dict() -> reader.TSurfData:
    """
    Create a dummy TSurfData object from a dictionary.
    It is assumed that the dictionary contains the same data as
    basic TSurf created by _create_basic_tsurf_file_as_lines().
    """

    tsurf_dict = {}
    tsurf_dict["header"] = {"name": "Fault F1"}
    tsurf_dict["coordinate_system"] = {
        "name": "Default",
        "axis_name": ("X", "Y", "Z"),
        "axis_unit": ("m", "m", "m"),
        "zpositive": "Depth",
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

    return reader.create_tsurf_from_dict(tsurf_dict)


def test_create_basic_tsurf_from_dict():
    """
    Test the instantiation of a TSurfData object from a dictionary.
    """

    instance = _create_basic_tsurf_from_dict()
    _validate_basic_tsurf(instance)


def test_tsurf_reader_writer(rootpath: Any):
    """
    Test the in-house TSurf reader/writer.
    """

    lines = _create_basic_tsurf_file_as_lines()
    lines = [line + "\n" for line in lines]

    # TODO: OK to save file in this folder?
    relpath = "tests/data/drogon/rms/output/structural/test_read_write.ts"
    filepath = rootpath / relpath
    assert not filepath.exists()

    # TODO: should filepath be a 'FilePath' object?

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as file:
        file.writelines(lines)
    assert filepath.exists()

    try:
        instance = reader.read_tsurf_file(filepath)
    finally:
        filepath.unlink(missing_ok=True)

    _validate_basic_tsurf(instance)


def test_tsurf_reader_comments_emptylines(rootpath: Any):
    """
    Test the in-house TSurf reader with comments and empty lines.
    """

    # TODO: OK to save file in this folder?
    relpath = (
        "tests/data/drogon/rms/output/structural/"
        "test_read_write_comments_emptylines_invalid_start.ts"
    )
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)

    lines = _create_basic_tsurf_file_as_lines()

    # Add comments and empty lines at arbitrary positions between and inside sections.
    # The first 'L' refers to the line number in the original file which the comment
    # should be placed before, the second 'L' refers to the line number in the
    # modified file after all new lines have been inserted
    comments = {
        0: "Invalid first line L_0 L_0",
        1: "# Test comment L_1 L_2",
        2: "# Test comment L_2 L_4",
        4: "# Test comment L_4 L_7",
        7: "# Test comment L_7 L_11",
        8: "# Test comment L_8 L_13",
        9: "# Test comment L_9 L_15",
        11: "# Test comment L_11 L_18",
        13: "# Test comment L_13 L_21",
        14: "# Test comment L_14 L_23",
        15: "# Test comment L_15 L_25",
        16: "# Test comment L_16 L_27",
        18: "# Test comment L_18 L_30",
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

    with pytest.raises(
        ValueError,
        match=(
            "The first line of the file indicates that this is not a valid TSurf file."
        ),
    ):
        reader.read_tsurf_file(filepath)

    filepath.unlink(missing_ok=True)

    # Remove the comment and empty line at the top
    # Continue testing the rest of the file with all its comments and empty lines
    valid_lines = new_lines_invalid_start[1:]

    # TODO: OK to save file in this folder?
    relpath = (
        "tests/data/drogon/rms/output/structural/test_read_write_comments_emptylines.ts"
    )
    filepath = rootpath / relpath
    assert not filepath.exists()

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as file:
        file.writelines(valid_lines)
    assert filepath.exists()

    try:
        instance = reader.read_tsurf_file(filepath)
    finally:
        filepath.unlink(missing_ok=True)

    _validate_basic_tsurf(instance)


def test_tsurf_reader_invalid_lines(rootpath: Any):
    """
    Test the in-house TSurf reader with invalid lines, namely anything
    that is not handled by the file parser such as TSurf keywords that
    are not handled, or just plain rubbish.
    """

    # TODO: should filepath be a 'FilePath' object?

    # TODO: OK to save file in this folder?
    relpath = (
        "tests/data/drogon/rms/output/structural/" "test_read_write_invalid_lines.ts"
    )
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)

    lines_1 = _create_basic_tsurf_file_as_lines()

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


def test_tsurf_reader_RMS_file(rootpath: Any):
    """
    Test the in-house TSurf reader/writer.
    """

    # The TSurf file 'F5.ts' was generated by RMS
    # TODO: OK to store RMS testfile in this folder?
    relpath = "tests/data/drogon/rms/output/structural/F5.ts"
    filepath = rootpath / relpath

    instance = reader.read_tsurf_file(filepath)

    assert instance.header.name == "F5"
    assert instance.coordinate_system.name == "Default"
    # TODO: use AllowedValues - everywhere in all tests
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
    with pytest.raises(ValidationError):
        header = reader.Header()

    # Pydantic has keyword only constructors, positional arguments are not allowed
    with pytest.raises(TypeError):
        header = reader.Header("Positional argument not allowed")

    # Invalid input parameter type
    with pytest.raises(ValidationError):
        header = reader.Header(name=73)

    # Invalid fields in header
    with pytest.raises(ValidationError):
        header = reader.Header(name="Fault F1", extra_field="invalid")

    ########################
    # Modify existing object
    ########################

    # Invalid input parameter type
    with pytest.raises(ValidationError):
        header = reader.Header(name=73)

    # Invalid input parameter type
    with pytest.raises(ValidationError):
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
    with pytest.raises(ValidationError):
        coord_sys = reader.CoordinateSystem(
            # Missing name
            axis_name=("X", "Y", "Z"),
            axis_unit=("m", "m", "m"),
            z_positive="Depth",
        )

    # Invalid field (axis_name only to elements)
    with pytest.raises(ValidationError):
        coord_sys = reader.CoordinateSystem(
            name="Default",
            axis_name=("X", "Y"),
            axis_unit=("m", "m", "m"),
            z_positive="Depth",
        )

    # Invalid field (axis_unit has element with invalid unit)
    with pytest.raises(ValidationError):
        coord_sys = reader.CoordinateSystem(
            name="Default",
            axis_name=("X", "Y", "Z"),
            axis_unit=("m", "nm", "m"),
            z_positive="Depth",
        )

    # Pydantic has keyword only constructors, positional arguments are not allowed
    with pytest.raises(TypeError):
        coord_sys = reader.CoordinateSystem(
            "Default", ("X", "Y", "Z"), ("m", "m", "m"), "Depth"
        )

    # Extra field is not allowed
    with pytest.raises(ValidationError):
        coord_sys = reader.CoordinateSystem(
            name="Default",
            axis_name=("X", "Y", "Z"),
            axis_unit=("m", "m", "km"),
            z_positive="Depth",
            is_imaginary=True,
        )

    # Invalid value type in field (axis_unit)
    with pytest.raises(ValidationError):
        coord_sys = reader.CoordinateSystem(
            name="Default",
            axis_name=("X", "Y", "Z"),
            axis_unit=np.ndarray([1, 2, 3]),
            z_positive="Depth",
        )

    # TODO: remove this test, is the same as below where checking that it raises
    # Invalid value type in field (z_positive)
    # TODO: why isn't the type checked before @field_validator?
    # Or should it be checked in the @field_validator?
    # Or should the class be a RootModel or something?
    coord_sys = reader.CoordinateSystem(
        name="Default",
        axis_name=("X", "Y", "Z"),
        axis_unit=("m", "m", "m"),
        z_positive=56,
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
    invalid_name_type = np.ndarray([1, 2, 3])
    with pytest.raises(ValidationError):
        coord_sys.name = invalid_name_type

    # Invalid value (2 elements instead of 3)
    invalid_axis_name = ("X", "Y")
    with pytest.raises(ValidationError):
        coord_sys.axis_name = invalid_axis_name

    # Invalid value (invalid unit)
    invalid_axis_unit = ("m", "m", "km")
    with pytest.raises(ValidationError):
        coord_sys.axis_unit = invalid_axis_unit

    # Invalid value
    invalid_z_positive = "Top"
    with pytest.raises(ValidationError):
        coord_sys.z_positive = invalid_z_positive

    # Invalid type
    invalid_z_positive_type = reader.Header(name="Fault F1")
    # TODO: why isn't the type checked before checking the value?
    coord_sys.z_positive = invalid_z_positive_type

    with pytest.raises(TypeError):
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
    # Validate fields
    #########################

    # Optional field missing (coordinate_system)
    assert reader.TSurfData(header=header, vertices=vertices, triangles=triangles)

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
    with pytest.raises(ValueError, match="'vertices' must be a numpy array"):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices="invalid",
            triangles=triangles,
        )

    with pytest.raises(
        ValueError, match="'vertices' must be a 2D matrix of size M x 3:"
    ):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=np.array([1.0, 2.0, 3.0]),
            triangles=triangles,
        )

    with pytest.raises(ValueError, match="'vertices' must be of type float64"):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=np.array([["invalid", 2.0, 3.0]]),
            triangles=triangles,
        )

    with pytest.raises(
        ValueError, match="'vertices' must contain at least three vertices"
    ):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=np.array([[1.0, 4.0, 5.0], [1.0, 5.0, 2.0]]),
            triangles=triangles,
        )

    ##########################
    # Validate triangles field
    ##########################
    with pytest.raises(ValueError, match="'triangles' must be a numpy array"):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles="invalid",
        )

    with pytest.raises(
        ValueError, match="'triangles' must be a 2D matrix of size M x 3:"
    ):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles=np.array([1, 2, 3]),  # 1 x 3 matrix
        )

    with pytest.raises(ValueError, match="'triangles' must be of type int64"):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles=np.array([["invalid", 2, 3]]),
        )

    with pytest.raises(
        ValueError, match="'triangles' must be a 2D matrix of size M x 3:"
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
        ValueError, match="Invalid vertex index in 'triangles': smaller than '1'"
    ):
        reader.TSurfData(
            header=header,
            coordinate_system=coord_sys,
            vertices=vertices,
            triangles=np.array([[1, 0, 1]]),
        )


def test_validation_tsurf_data_modification():
    """
    Test the validation of the TSurf data when modifying an existing object.
    """

    instance1 = _create_basic_tsurf_from_dict()

    # Valid type
    instance1.header = reader.Header(name="Fault F2")

    # Invalid type
    with pytest.raises(ValidationError, match="Invalid header"):
        instance1.header = "Invalid header"

    # Optional field, so OK to set to None
    instance1.coordinate_system = None

    instance1 = _create_basic_tsurf_from_dict()
    with pytest.raises(ValidationError, match="Invalid 'AXIS_NAME' value"):
        instance1.coordinate_system.axis_name = ("X", "Y", "ZZZZZZ")

    # Change vertices
    instance1 = _create_basic_tsurf_from_dict()
    # Type and structure are valid, should not raise an error
    instance1.vertices = np.array(
        [
            (5.1, 5.2, 5.3),
            (6.1, 6.2, 6.3),
            (7.1, 7.2, 7.3),
        ]
    ).astype(np.float64)

    # Invalid type
    with pytest.raises(AssertionError):
        # TODO: assigning new value of invalid type should raise an error,
        # to ensure the same behaviour as when instantiating an object.
        # But the field is not validated by Pydantic
        # I could make a get/set and check the type there?
        instance1.vertices = "invalid_type"

    # Invalid structure
    with pytest.raises(AssertionError):
        # Same as for ##instance1.vertices = "invalid_type"## above
        instance1.vertices = np.zeros((2, 2), dtype=np.float64)

    # Change triangles
    instance1 = _create_basic_tsurf_from_dict()
    # Type and structure are valid, should not raise an error
    instance1.triangles = np.array(
        [
            (5, 7, 2),
        ]
    ).astype(np.int64)

    # Invalid type
    with pytest.raises(AssertionError):
        instance1.triangles = 54

    # Invalid structure
    with pytest.raises(AssertionError):
        instance1.vertices = np.zeros((2, 2), dtype=np.int64)


def test_tsurf_data_equality():
    """Test the equality of TSurfData objects."""

    # TODO: Matthew: OK with shallow test of equality?

    # Create two identical instances
    instance1 = _create_basic_tsurf_from_dict()
    instance2 = _create_basic_tsurf_from_dict()

    # Test equality
    assert instance1 == instance2

    # instance1 and instance3 refer to the same object
    instance3 = instance1
    assert instance1 == instance3

    # Change header
    instance2 = _create_basic_tsurf_from_dict()
    with pytest.raises(AssertionError):
        instance2.header.name = "Fault F2"
        assert instance1 == instance2

    # Coordinate system exists in one but not in the other
    # Should throw as the coordinate systems are not equal,
    # even though the field is optional
    instance2 = _create_basic_tsurf_from_dict()
    instance2.coordinate_system = None
    with pytest.raises(AssertionError):
        assert instance1 == instance2

    # Change vertex value
    # The equality check does not consider the values, only the structure,
    # so this should pass
    instance2 = _create_basic_tsurf_from_dict()
    instance2.vertices[0, 2] = np.nan
    assert instance1 == instance2

    # Change triangle index value
    # The equality check does not consider the values, only the structure,
    # so this should pass
    instance2 = _create_basic_tsurf_from_dict()
    instance2.triangles[0, 2] = instance1.triangles[0, 2] + 1
    assert instance1 == instance2

    instance2 = _create_basic_tsurf_from_dict()
    # Only the first triangle, so the shape of the arrays are different
    instance2.triangles = instance1.triangles[:-1]
    with pytest.raises(AssertionError):
        assert instance1 == instance2

    # Extra fields
    instance2 = _create_basic_tsurf_from_dict()
    instance2.extra_field = "invalid"
    # Extra fields are allowed, but since they are ignored by the class
    # the instances are considered equal
    assert instance1 == instance2
