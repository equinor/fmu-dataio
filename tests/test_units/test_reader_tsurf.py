from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from fmu.dataio._readers import tsurf as reader


def _create_hardcoded_file(filepath: Path):
    """
    Create a hardcoded TSurf file for testing purposes.
    The file contains only data that are supported by the reader.
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
TFACE
VRTX 1 0.1 0.2 0.3 CNXYZ
VRTX 2 1.1 1.2 1.3 CNXYZ
VRTX 3 2.1 2.2 2.3 CNXYZ
VRTX 4 3.1 3.2 3.3 CNXYZ
TRGL 1 2 3
TRGL 1 2 4
END
""")


def _create_hardcoded_file_comments(filepath: Path):
    """
    Create a hardcoded TSurf file for testing purposes.
    The file contains only data that are supported by the reader.
    But it also contains comments in various places.
    """

    with open(filepath, "w") as file:
        file.write("""# Test comment
GOCAD TSurf 1
HEADER {
# Test comment
name: Fault F1
# Test comment
}
# Test comment
GOCAD_ORIGINAL_COORDINATE_SYSTEM
NAME Default
# Test comment
AXIS_NAME "X" "Y" "Z"
AXIS_UNIT "m" "m" "m"
# Should handle empty lines (next line)
                   
ZPOSITIVE Depth
END_ORIGINAL_COORDINATE_SYSTEM
# Test comment
TFACE
VRTX 1 0.1 0.2 0.3 CNXYZ
VRTX 2 1.1 1.2 1.3 CNXYZ
# Test comment
VRTX 3 2.1 2.2 2.3 CNXYZ
VRTX 4 3.1 3.2 3.3 CNXYZ
TRGL 1 2 3
TRGL 1 2 4
# Test comment
END
# Test comment
""")


def _create_hardcoded_file_unsupported_entries(filepath: Path):
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


def _create_tsurfdata_instance() -> reader.TSurfData:
    """Create a dummy TSurfData object for testing purposes."""

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

    return reader.create_tsurf_filedata(tsurf_dict)


def test_create_tsurfdata_instance():
    """
    Test the instantiation of a TSurfData object.
    This will trigger the Pydantic tests
    """

    instance = _create_tsurfdata_instance()

    # Test the data
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


def test_tsurf_reader_writer_hardcoded_file(rootpath: Any):
    """Test the in-house TSurf reader/writer."""

    # TODO: OK to save file in this folder?
    relpath = "tests/data/drogon/rms/output/structural/hardcoded.ts"
    filepath = rootpath / relpath

    # TODO: also test _create_hardcoded_file_unsupported_entries(): in a loop to avoid repetition?
    # and _create_hardcoded_file_comments()
    _create_hardcoded_file(filepath)
    assert filepath.exists()

    try:
        instance = reader.read_tsurf_file(filepath)

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

    finally:
        # Remove the file
        filepath.unlink()
        assert not filepath.exists()


def test_tsurf_reader_RMS_file(rootpath: Any):
    """Test the in-house TSurf reader/writer."""

    # The TSurf file 'F5.ts' was generated by RMS
    relpath = "tests/data/drogon/rms/output/structural/F5.ts"
    filepath = rootpath / relpath

    instance = reader.read_tsurf_file(filepath)

    assert instance.header.name == "F5"
    assert instance.coordinate_system.name == "Default"
    assert instance.coordinate_system.axis_name == ("X", "Y", "Z")
    assert instance.coordinate_system.axis_unit == ("m", "m", "m")
    assert instance.coordinate_system.z_positive == "Depth"
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


def test_tsurf_writer(rootpath: Any):
    """Test the in-house TSurf writer."""

    instance = _create_tsurfdata_instance()
    relpath = "tests/data/drogon/rms/output/structural/dummy.ts"
    filepath = rootpath / relpath

    try:
        reader.write_tsurf_file(instance, filepath)
        read_instance = reader.read_tsurf_file(filepath)
        assert instance == read_instance

    finally:
        # Remove the file
        filepath.unlink()
        assert not filepath.exists()


# def test_tsurf_writer_without_coordinate_system(rootpath: Any):
#     """
#     Test the in-house TSurf writer when the coordinate system is not provided.
#     """

#     instance = _create_tsurfdata_instance()
#     instance.coordinate_system = None
#     relpath = "tests/data/drogon/rms/output/structural/dummy_no_coord_system.ts"
#     filepath = rootpath / relpath

#     try:
#         reader.write_tsurf_file(instance, filepath)
#         read_instance = reader.read_tsurf_file(filepath)
#         assert instance == read_instance

#     finally:
#         # Remove the file
#         filepath.unlink()
#         assert not filepath.exists()


def test_validation_header():
    """Test the TSurf data validation of the header."""

    # Instantiation
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


def test_validation_coordinate_system():
    """Test the TSurf data validation of the coordinate system."""

    # Instantiation
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

    # Update
    coord_sys.name = "Another name"
    assert coord_sys.name == "Another name"

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

    # Extra field
    # TODO: the user may provide extra fields in compliance with the GOCAD format,
    # ensure that this raises a ValidationError
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


def test_validation_tsurf_file_data():
    """Test the validation of the TSurf file data."""

    # Instantiation of each parameter, then of the class
    header = reader.Header(name="Fault F1")
    coord_sys = reader.CoordinateSystem(
        name="Default",
        axis_name=("X", "Y", "Z"),
        axis_unit=("m", "m", "m"),
        z_positive="Depth",
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
    assert instance.coordinate_system.axis_name == ("X", "Y", "Z")

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


def test_tsurfdata_equality():
    """Test the equality of TSurfData objects."""

    # TODO: autogenerated, check if it is correct

    # Create two identical instances
    instance1 = _create_tsurfdata_instance()
    instance2 = _create_tsurfdata_instance()

    # Test equality
    assert instance1 == instance2

    # Change header
    with pytest.raises(AssertionError):
        instance2.header.name = "Fault F2"
        assert instance1 == instance2

    # Different type in header
    # TODO: should not be allowed to have a different type
    with pytest.raises(AssertionError):
        instance2.header = 93
        assert instance1 == instance2

    # Coordinate system exists in one but not in the other
    instance2 = _create_tsurfdata_instance()
    instance2.coordinate_system = None
    with pytest.raises(AssertionError):
        assert instance1 == instance2

    instance2 = _create_tsurfdata_instance()
    instance2.vertices[0, 2] = np.nan
    with pytest.raises(AssertionError):
        assert instance1 == instance2

    instance2 = _create_tsurfdata_instance()
    instance2.triangles[0, 2] = instance1.triangles[0, 2] + 1
    with pytest.raises(AssertionError):
        assert instance1 == instance2
