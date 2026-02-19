"""Resolves Pydantic model field annotations for autosummary."""

import importlib
from collections.abc import Sequence
from enum import Enum
from functools import lru_cache
from typing import Any, NamedTuple, get_args, get_origin

from pydantic import BaseModel


class FieldAnnotations(NamedTuple):
    """Annotation strings split by kind."""

    models: tuple[str, ...]
    enums: tuple[str, ...]


def _belongs_to_packages(annotation: Any, packages: tuple[str, ...]) -> bool:
    """Returns True if annotation belongs to one of the package prefixes."""
    if annotation is None or not packages:
        return False
    if isinstance(annotation, str):
        return any(annotation.startswith(p) for p in packages)
    module = getattr(annotation, "__module__", None)
    if module is None:
        return False
    return any(module.startswith(p) for p in packages)


def _is_enum_class(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, Enum)


def _is_enum_member(annotation: Any) -> bool:
    return isinstance(annotation, Enum)


def _can_import_object(module_path: str, attr_name: str, target: Any) -> bool:
    try:
        mod = importlib.import_module(module_path)
    except Exception:
        return False
    return getattr(mod, attr_name, None) is target


@lru_cache
def _resolve_importable_name(annotation: Any) -> str:
    """Return the shortest fully qualified name where 'annotation' is importable."""
    module_name: str | None = getattr(annotation, "__module__", None)
    qualname: str | None = getattr(annotation, "__qualname__", None)

    if module_name is None or qualname is None:
        return repr(annotation)

    attr_name = qualname.rsplit(".", 1)[-1]
    canonical = f"{module_name}.{qualname}"

    parts = module_name.split(".")
    best: str | None = None
    for i in range(len(parts), 0, -1):
        candidate_module = ".".join(parts[:i])
        if _can_import_object(candidate_module, attr_name, annotation):
            best = f"{candidate_module}.{attr_name}"

    if best is None:
        return canonical
    return best


def _walk(
    annotation: Any,
    packages: tuple[str, ...],
    models: list[str],
    enums: list[str],
    seen: set[int],
) -> None:
    """DFS walk of a possibly generic type annotation."""
    if annotation is None:
        return

    ann_id = id(annotation)
    if ann_id in seen:
        return
    seen.add(ann_id)

    if _is_enum_class(annotation):
        if _belongs_to_packages(annotation, packages):
            enums.append(_resolve_importable_name(annotation))
        return

    if _is_enum_member(annotation):
        enum_cls = type(annotation)
        cls_id = id(enum_cls)
        if cls_id not in seen:
            seen.add(cls_id)
            if _belongs_to_packages(enum_cls, packages):
                enums.append(_resolve_importable_name(enum_cls))
        return

    if _belongs_to_packages(annotation, packages):
        models.append(_resolve_importable_name(annotation))

    origin = get_origin(annotation)
    if origin is not None:
        origin_id = id(origin)
        if origin_id not in seen:
            seen.add(origin_id)
            if _belongs_to_packages(origin, packages):
                models.append(_resolve_importable_name(origin))

    for arg in get_args(annotation):
        _walk(arg, packages, models, enums, seen)


def _resolve_field_annotation(
    annotation: Any,
    packages: tuple[str, ...],
    seen: set[int],
) -> tuple[list[str], list[str]]:
    """Resolve a single field annotation into (models, enums) lists."""
    models: list[str] = []
    enums: list[str] = []
    _walk(annotation, packages, models, enums, seen=seen)
    return models, enums


@lru_cache
def _cached_model_fields(
    model_cls: BaseModel, packages: tuple[str, ...]
) -> FieldAnnotations:
    """Return deduplicated annotation strings."""
    all_models: list[str] = []
    all_enums: list[str] = []
    seen: set[int] = set()

    for field in model_cls.model_fields.values():
        models, enums = _resolve_field_annotation(field.annotation, packages, seen)
        all_models.extend(models)
        all_enums.extend(enums)

    return FieldAnnotations(
        models=tuple(dict.fromkeys(all_models)),
        enums=tuple(dict.fromkeys(all_enums)),
    )


def set_pydantic_model_fields(
    ns: dict[str, Any], obj: Any, *, packages: Sequence[str] = ()
) -> None:
    ns["obj"] = obj
    ns["is_int"] = issubclass(obj, int)
    ns["is_str"] = issubclass(obj, str)

    annotations = _cached_model_fields(obj, tuple(packages))

    seen_models: dict[str, str] = {}
    for field in annotations.models:
        short = field.rsplit(".", 1)[-1]
        if short not in seen_models:
            seen_models[short] = field

    seen_enums: dict[str, str] = {}
    for enum in annotations.enums:
        short = enum.rsplit(".", 1)[-1]
        if short not in seen_enums:
            seen_models[short] = enum

    ns["model_fields"] = list(seen_models.values())
    ns["model_enums"] = list(seen_enums.values())
