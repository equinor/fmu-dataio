from fmu.dataio.exceptions import ValidationError


def test_validation_error_str_preserves_line_breaks() -> None:
    err = ValidationError("line one\nline two")

    assert str(err) == "line one\nline two"


def test_validation_error_str_is_not_keyerror_repr() -> None:
    err = ValidationError("hello")

    assert str(err) == "hello"
    assert str(err) != "'hello'"
