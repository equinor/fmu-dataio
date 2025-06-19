from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from fmu.dataio._readers import tsurf as reader


def _validate_tsurf(instance: reader.TSurfData) -> None:
    """
    Validate a basic TSurf object.
    """
    assert isinstance(instance, reader.TSurfData)
    assert instance.header.name == "Fault F1"
    assert (
        instance.coordinate_system is not None
        and instance.coordinate_system.name == "Default"
    )
    assert (
        instance.coordinate_system is not None
        and instance.coordinate_system.axis_name == ("X", "Y", "Z")
    )
    assert (
        instance.coordinate_system is not None
        and instance.coordinate_system.axis_unit == ("m", "m", "m")
    )
    assert (
        instance.coordinate_system is not None
        and instance.coordinate_system.z_positive == "Depth"
    )
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


def _insert_new_lines(lines: list[str], extra: dict[int, str]) -> list[str]:
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


def test_create_tsurf(tsurf: reader.TSurfData) -> None:
    """
    Test the instantiation of a TSurfData object from a dictionary.
    """

    _validate_tsurf(tsurf)


def test_tsurf_reader_and_writer(tsurf: reader.TSurfData, rootpath: Path) -> None:
    """
    Test the TSurf reader and writer.
    """

    # ---------- Test with a directory, which is not a regular file
    relpath = "tests/data/drogon/rms/output/structural/invalid_dir"
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)
    filepath.mkdir(parents=True, exist_ok=True)
    with pytest.raises(
        FileNotFoundError,
        match="The file is not a regular file",
    ):
        reader.read_tsurf_file(filepath)
    filepath.rmdir()

    relpath = "tests/data/drogon/rms/output/structural/invalid_suffix.txt"
    filepath = rootpath / relpath
    filepath.unlink(missing_ok=True)

    # ---------- File does not exists ----------
    with pytest.raises(
        FileNotFoundError,
        match="The file does not exist",
    ):
        reader.read_tsurf_file(filepath)

    # ---------- Wrong file suffix ----------
    reader.write_tsurf_to_file(tsurf, filepath)
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

    # ---------- Empty file ----------
    filepath.touch()
    with pytest.raises(
        ValueError,
        match="Input is empty",
    ):
        reader.read_tsurf_file(filepath)

    # ---------- Filepath as string ----------
    filepath_str = str(filepath)
    with pytest.raises(
        ValueError,
        match="Input is empty",
    ):
        reader.read_tsurf_file(filepath_str)
    filepath.unlink(missing_ok=True)

    # ---------- Invalid input ----------
    with pytest.raises(
        TypeError,
        match="The input must be a Path or a BytesIO object.",
    ):
        random_int = 42
        reader.read_tsurf_file(random_int)

    # ---------- File with valid content ----------
    reader.write_tsurf_to_file(tsurf, filepath)
    assert filepath.exists()

    instance_from_file = reader.read_tsurf_file(filepath)
    filepath.unlink(missing_ok=True)

    _validate_tsurf(instance_from_file)

    # ---------- Memory buffer with valid content ----------
    buffer = BytesIO()
    reader.write_tsurf_to_file(tsurf, buffer)
    instance_from_buffer = reader.read_tsurf_file(buffer)
    buffer.close()

    _validate_tsurf(instance_from_buffer)

    # ---------- Check of equality operator ----------
    assert instance_from_file == instance_from_buffer


def test_tsurf_class_methods(tsurf: reader.TSurfData, rootpath: Path) -> None:
    """
    Test class methods
    """

    assert tsurf.num_vertices() == 4
    assert tsurf.num_triangles() == 2
    assert tsurf.bbox() == {
        "xmin": 0.1,
        "xmax": 3.1,
        "ymin": 0.2,
        "ymax": 3.2,
        "zmin": 0.3,
        "zmax": 3.3,
    }


def test_tsurf_reader_comments_emptylines(
    tmp_path: Path, tsurf_as_lines: list[str]
) -> None:
    """
    Test the reader with comments and empty lines in the file.
    """

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

    lines = _insert_new_lines(tsurf_as_lines, comments)

    empty_lines = {
        1: "",
        4: "",
        10: "",
        11: "",
        17: "",
    }

    # Two first lines: comment and empty line
    new_lines_invalid_start = _insert_new_lines(lines, empty_lines)
    new_lines_invalid_start = [line + "\n" for line in new_lines_invalid_start]

    filepath = tmp_path / "test_read_write_comments_emptylines_invalid_start.ts"
    with open(filepath, "w") as file:
        file.writelines(new_lines_invalid_start)

    # Ensure the file parser handles the first lines correctly
    with pytest.raises(
        ValueError,
        match=("The first line indicates"),
    ):
        reader.read_tsurf_file(filepath)

    # Remove the invalid first two lines
    # Continue testing the rest of the file with all its comments and empty lines
    valid_lines = new_lines_invalid_start[1:]

    filepath = tmp_path / "test_read_write_comments_emptylines.ts"
    with open(filepath, "w") as file:
        file.writelines(valid_lines)

    instance = reader.read_tsurf_file(filepath)
    _validate_tsurf(instance)


def test_tsurf_reader_invalid_lines(tmp_path: Path, tsurf_as_lines: list[str]) -> None:
    """
    Test the reader with invalid lines:
    - TSurf keywords that are allowed by the file format but are
      not (yet) handled but this reader
    - plain rubbish
    """

    # Add invalid lines at arbitrary positions between and inside sections
    # Note that 'WELL_CURVE' and 'GEOLOGICAL_FEATURE' are allowed TSurf keywords
    # but are not handled by this reader
    invalid_lines = {
        1: "WELL_CURVE",
        6: "Rubbish",
        8: "GEOLOGICAL_FEATURE",
        14: "Rubbish",
    }
    lines_2 = _insert_new_lines(tsurf_as_lines, invalid_lines)
    lines_3 = [line + "\n" for line in lines_2]

    filepath = tmp_path / "test_read_write_invalid_lines.ts"
    with open(filepath, "w") as file:
        file.writelines(lines_3)

    with pytest.raises(
        ValueError,
        match="This may be either an error, or a valid TSurf keyword or attribute",
    ):
        reader.read_tsurf_file(filepath)


def test_parsing_file_with_errors_header_section_1(
    tmp_path: Path, tsurf_as_lines: list[str]
) -> None:
    """
    Test the file parser with a TSurf file that should produce
    errors: header is missing 'name'.
    """

    # Error: header is missing line with 'name'
    invalid_lines = [line if "name" not in line else "" for line in tsurf_as_lines]
    invalid_lines = [line + "\n" for line in invalid_lines]

    filepath = tmp_path / "basic_tsurf_file_with_errors_header_1.ts"
    with open(filepath, "w") as file:
        file.writelines(invalid_lines)

    with pytest.raises(
        ValueError,
        match="is expected to have exactly one attribute: 'name'",
    ):
        reader.read_tsurf_file(filepath)


def test_parsing_file_with_errors_header_section_2(
    tmp_path: Path, tsurf_as_lines: list[str]
) -> None:
    """
    Test the file parser with a TSurf file that should produce
    errors: header has an extra keyword.
    """

    # Error: header has an extra keyword
    # Keep the name line, add an extra keyword line
    invalid_lines = tsurf_as_lines.copy()
    replace_lines = ["name: Fault F1", "extra_keyword: extra_value"]
    idx = invalid_lines.index("name: Fault F1")
    if idx > -1:
        invalid_lines[idx] = replace_lines[0]
        invalid_lines.insert(idx + 1, replace_lines[1])
    invalid_lines = [line + "\n" for line in invalid_lines]

    filepath = tmp_path / "basic_tsurf_file_with_errors_header_2.ts"
    with open(filepath, "w") as file:
        file.writelines(invalid_lines)

    with pytest.raises(
        ValueError,
        match="is expected to have exactly one attribute: 'name'",
    ):
        reader.read_tsurf_file(filepath)


def test_parsing_file_with_errors_coordinate_system_section_1(
    tmp_path: Path, tsurf_as_lines: list[str]
) -> None:
    """
    Test the file parser with a TSurf file that should produce
    errors: ZPOSITIVE value is incorrect.
    """

    # Error: ZPOSITIVE value is invalid
    invalid_lines = [
        line if "ZPOSITIVE" not in line else "ZPOSITIVE error"
        for line in tsurf_as_lines
    ]
    invalid_lines = [line + "\n" for line in invalid_lines]

    filepath = tmp_path / "basic_tsurf_file_with_errors_coordsys_1.ts"
    with open(filepath, "w") as file:
        file.writelines(invalid_lines)

    with pytest.raises(ValueError, match="Invalid 'ZPOSITIVE' value"):
        reader.read_tsurf_file(filepath)


def test_parsing_file_with_errors_coordinate_system_section_2(
    tmp_path: Path, tsurf_as_lines: list[str]
) -> None:
    """
    Test the file parser with a TSurf file that should produce
    errors: ZPOSITIVE line is missing so that the COORDINATE_SYSTEM
    section is incomplete.
    """

    # Error: missing line ZPOSITIVE
    invalid_lines = [line if "ZPOSITIVE" not in line else "" for line in tsurf_as_lines]
    invalid_lines = [line + "\n" for line in invalid_lines]

    filepath = tmp_path / "basic_tsurf_file_with_errors_coordsys_2.ts"
    with open(filepath, "w") as file:
        file.writelines(invalid_lines)

    with pytest.raises(ValueError, match="Invalid 'COORDINATE_SYSTEM' section"):
        reader.read_tsurf_file(filepath)


def test_parsing_file_with_errors_coordinate_system_section_3(
    tmp_path: Path, tsurf_as_lines: list[str]
) -> None:
    """
    Test the file parser with a TSurf file that should produce
    errors: coordinate system section contains an invalid keyword.
    """

    # Error: missing line ZPOSITIVE
    invalid_lines = [
        line if "AXIS_NAME" not in line else "INVALID_KEYWORD error"
        for line in tsurf_as_lines
    ]
    invalid_lines = [line + "\n" for line in invalid_lines]

    filepath = tmp_path / "basic_tsurf_file_with_errors_coordsys_3.ts"
    with open(filepath, "w") as file:
        file.writelines(invalid_lines)

    with pytest.raises(ValueError, match="Invalid 'COORDINATE_SYSTEM' section"):
        reader.read_tsurf_file(filepath)


def test_parsing_file_with_errors_tface_section(
    tmp_path: Path, tsurf_as_lines: list[str]
) -> None:
    """
    Test the file parser with a TSurf file that should produce
    errors: in the TFACE section, the lines with vertices do not
    start with the keyword 'VRTX'.
    Instead they start with 'PVRTX', which is a valid TSurf keyword,
    but not handled by this reader.
    """

    # Error: 'VRTX' is replaced by 'PVRTX'
    invalid_lines = [
        line if "VRTX" not in line else line.replace("VRTX", "PVRTX")
        for line in tsurf_as_lines
    ]
    invalid_lines = [line + "\n" for line in invalid_lines]

    filepath = tmp_path / "basic_tsurf_file_with_errors_tface.ts"
    with open(filepath, "w") as file:
        file.writelines(invalid_lines)

    with pytest.raises(
        ValueError, match="Invalid line in 'TFACE' section with triangulated data"
    ):
        reader.read_tsurf_file(filepath)


def test_parsing_file_with_warnings(tmp_path: Path, tsurf_as_lines: list[str]) -> None:
    """
    Test the file parser with a TSurf file with content that should produce
    warnings.
    """

    # Uncommon value for AXIS_UNIT
    uncommon_lines = [
        line if "AXIS_UNIT" not in line else 'AXIS_UNIT "m" "cm" "m"'
        for line in tsurf_as_lines
    ]
    uncommon_lines = [line + "\n" for line in uncommon_lines]

    filepath = tmp_path / "basic_tsurf_file_with_warnings.ts"
    with open(filepath, "w") as file:
        file.writelines(uncommon_lines)
    with pytest.warns(UserWarning, match="Uncommon 'AXIS_UNIT' value"):
        reader.read_tsurf_file(filepath)


def test_tsurf_reader_RMS_file(rootpath: Path) -> None:
    """
    Test the reader with a TSurf file generated by RMS.
    """

    relpath = Path("tests/data/drogon/rms/output/structural/F5.ts")
    filepath = rootpath / relpath

    instance = reader.read_tsurf_file(filepath)

    assert instance.header.name == "F5"
    assert (
        instance.coordinate_system is not None
        and instance.coordinate_system.name == "Default"
    )
    assert instance.coordinate_system is not None and (
        instance.coordinate_system.axis_name
        == reader.AllowedKeywordValues.axis_names["xyz"]
    )
    assert instance.coordinate_system is not None and (
        instance.coordinate_system.axis_unit
        == reader.AllowedKeywordValues.axis_units["mmm"]
    )
    assert instance.coordinate_system is not None and (
        instance.coordinate_system.z_positive
        == reader.AllowedKeywordValues.z_positives["depth"]
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


def test_validation_header() -> None:
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


def test_validation_coordinate_system() -> None:
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


def test_validation_tsurf_instantiation() -> None:
    """
    Test the validation of the TSurf data when creating new objects.
    """

    header = reader.Header(name="Fault F1")
    coord_sys = reader.CoordinateSystem(
        name="Default",
        axis_name=reader.AllowedKeywordValues.axis_names["xyz"],
        axis_unit=reader.AllowedKeywordValues.axis_units["mmm"],
        z_positive=reader.AllowedKeywordValues.z_positives["depth"],
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
        instance.coordinate_system is not None
        and instance.coordinate_system.axis_name
        == reader.AllowedKeywordValues.axis_names["xyz"]
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

    # A few simple checks to avoid common mistakes

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


def test_validation_tsurf_data_modification(tsurf: reader.TSurfData) -> None:
    """
    Test the validation when modifying an existing object.
    """

    # Nice to consider: when trying to modify a field within a 'with pytest.raises()'
    # clause, the validation fails, field is not modified and the object is still valid

    # Invalid type
    with pytest.raises(ValidationError, match="Invalid header"):
        tsurf.header = "Invalid header type"

    with pytest.warns(UserWarning, match="Uncommon 'AXIS_NAME' value:"):
        tsurf.coordinate_system.axis_name = ("X", "Y", "ZZZZZZ")

    # Change vertices: type and structure are valid, should not raise an error
    tsurf.vertices = np.array(
        [
            (5.1, 5.2, 5.3),
            (6.1, 6.2, 6.3),
            (7.1, 7.2, 7.3),
        ]
    ).astype(np.float64)

    # Invalid vertices type
    with pytest.raises(ValidationError, match="'vertices' must be a numpy array"):
        tsurf.vertices = "invalid_type"

    # Invalid structure
    with pytest.raises(
        ValidationError, match="'vertices' must be a 2D matrix of size M x 3:"
    ):
        tsurf.vertices = np.zeros((2, 2), dtype=np.float64)

    # Invalid numpy type
    with pytest.raises(
        ValidationError, match="'vertices' array must be of type float64"
    ):
        tsurf.vertices = np.array(
            [
                (5.1, 5.2, 5.3),
                (6.1, 6.2, 6.3),
                (7.1, 7.2, 7.3),
            ]
        ).astype(np.float32)

    # Change triangles: type and structure are valid, should not raise an error
    tsurf.triangles = np.array(
        [
            (5, 7, 2),
        ]
    ).astype(np.int64)

    # Invalid type
    with pytest.raises(ValidationError, match="'triangles' must be a numpy array"):
        tsurf.triangles = 54

    # Invalid structure
    with pytest.raises(
        ValidationError, match="'triangles' must be a 2D matrix of size M x 3:"
    ):
        tsurf.triangles = np.zeros((2, 2), dtype=np.int64)

    # Invalid numpy type
    with pytest.raises(
        ValidationError, match="'triangles' array must be of type int64"
    ):
        tsurf.triangles = np.array(
            [
                (5, 7, 2),
            ]
        ).astype(np.int8)


def test_validation_tsurf_data_equality(tsurf: reader.TSurfData) -> None:
    """
    Test the equality of TSurfData objects.
    For the triangulated data, only the structure of the numpy arrays is considered,
    not the values.
    """

    # Two identical instances
    instance1 = tsurf
    instance2 = tsurf.model_copy(deep=True)

    assert instance1 != 56

    assert instance1 is not instance2

    # Test equality operator
    assert instance1 == instance2

    # instance1 and instance3 refer to the same object,
    # should be handled by the equality operator
    instance3 = instance1
    assert instance1 == instance3

    # Change property object, but with equal values: should be OK
    tmp = instance2.header
    instance2.header = reader.Header(name=instance1.header.name)
    assert instance1 == instance2
    instance2.header = tmp

    # Change value in property object: should raise an error
    tmp = instance2.header.name
    instance2.header.name = "BCU"
    assert instance1 != instance2
    instance2.header.name = tmp

    # Should raise an error as the coordinate systems are not equal,
    # even though the field is optional
    tmp = instance2.coordinate_system.name
    instance2.coordinate_system.name = "cylindrical"
    assert instance1 != instance2
    instance2.coordinate_system.name = tmp

    # Coordinate system exists in one but not in the other
    # Should raise an error as the coordinate systems are not equal,
    # even though the field is optional
    tmp = instance2.coordinate_system
    instance2.coordinate_system = None
    assert instance1 != instance2
    instance2.coordinate_system = tmp

    # Change vertex value
    # The equality operator does not consider the values, only the matrix structure,
    # so this should pass
    instance2.vertices[0, 2] = instance2.vertices[0, 2] + 1
    assert instance1 == instance2

    # Change triangle index value
    # The equality check does not consider the values, only the matrix structure,
    # so this should pass
    instance2.triangles[0, 2] = instance1.triangles[0, 2] + 1
    assert instance1 == instance2

    # Only the first triangle, so the shape of the arrays are different
    tmp = instance2.triangles
    instance2.triangles = instance1.triangles[:-1]
    assert instance1 != instance2
    instance2.triangles = tmp

    # Extra fields
    instance2.extra_field = "extra_field"
    # Extra fields are allowed, but since they are ignored by the class
    # the instances are considered equal
    assert instance1 == instance2
