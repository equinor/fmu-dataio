from __future__ import annotations

from enum import Enum
from typing import Any, Final, get_args, get_origin

_DATAIO_METADATA_PACKAGE: Final = "fmu.dataio._model"


def _is_dataio(annotation: Any) -> bool:
    if isinstance(annotation, str):
        return annotation.startswith(_DATAIO_METADATA_PACKAGE)
    return annotation.__module__.startswith(_DATAIO_METADATA_PACKAGE)


def _is_enum_or_enum_member(annotation: Any) -> bool:
    return (isinstance(annotation, type) and issubclass(annotation, Enum)) or (
        isinstance(type(annotation), type) and issubclass(type(annotation), Enum)
    )


def _format_annotation(annotation: Any) -> str:
    return f"{annotation.__module__}.{annotation.__qualname__}"


def _resolve_pydantic_field_annotations(annotation: Any) -> list[str]:
    """Returns a list of Pydantic submodels used as fields for a given Pydantic
    model."""
    # Enums aren't Pydantic but found in the same place
    if _is_enum_or_enum_member(annotation):
        return []

    # Get the unsubscripted version of a type: for a typing object of the
    # form: X[Y, Z, ...], return X.
    origin = get_origin(annotation)

    annotations: list[str] = []
    if _is_dataio(annotation):
        annotations.append(_format_annotation(annotation))
    if origin and _is_dataio(origin):
        annotations.append(_format_annotation(origin))

    # Get type arguments with all substitutions performed: for a typing object of the
    # form: X[Y, Z, ...], return (Y, Z, ...).
    for arg in get_args(annotation):
        if _is_enum_or_enum_member(arg):
            continue
        if _is_dataio(arg):
            annotations.append(_format_annotation(arg))
        # TODO: recurse into arg for things that might be nested more deeply, i.e.
        # Optional[Union[List[...]]]

    return annotations


def set_pydantic_model_fields(ns: dict[str, Any], obj: Any) -> None:
    ns["obj"] = obj
    ns["is_int"] = issubclass(obj, int)
    ns["is_str"] = issubclass(obj, str)

    annotations = []
    for field in obj.model_fields.values():
        annotations += _resolve_pydantic_field_annotations(field.annotation)

    ns["model_fields"] = list(set(annotations))
