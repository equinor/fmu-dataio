import pyarrow as pa
import pytest

from fmu.dataio._workflows.case._parameters import _resolve_pa_field_type


def test_resolve_pa_field_type_realization_col() -> None:
    assert _resolve_pa_field_type("REAL", pa.int64()) == pa.int32()


@pytest.mark.parametrize(
    "pa_type, expected",
    [
        (pa.large_string(), pa.string()),
        (pa.string(), pa.string()),
        (pa.large_utf8(), pa.utf8()),
        (pa.utf8(), pa.utf8()),
        (pa.float32(), pa.float32()),
    ],
)
def test_resolve_pa_field_type_smaller_dtypes(
    pa_type: pa.DataType, expected: pa.DataType
) -> None:
    assert _resolve_pa_field_type("foo", pa_type) == expected
