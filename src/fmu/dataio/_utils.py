"""Module for private utilities/helpers for DataIO class."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Final

import numpy as np
import xtgeo

from fmu.config import utilities as ut

from . import types
from ._logging import null_logger

logger: Final = null_logger(__name__)


def npfloat_to_float(v: Any) -> Any:
    return float(v) if isinstance(v, (np.float64, np.float32)) else v


def detect_inside_rms() -> bool:
    """Detect if 'truly' inside RMS GUI, where predefined variable project exist.

    However this will be overriden by an environment variable for unit testing
    when using the Roxar API python, so that unit test outside of RMS behaves
    properly
    """
    with contextlib.suppress(ModuleNotFoundError):
        import roxar

        logger.info("Roxar version is %s", roxar.__version__)
        return True
    logger.info("Running truly in RMS GUI status: %s", False)
    return False


def dataio_examples() -> bool:
    # This flag is set when the `run-exmaples.sh` script runs.
    return "RUN_DATAIO_EXAMPLES" in os.environ


def drop_nones(dinput: dict) -> dict:
    """Recursively drop Nones in dict dinput and return a new dict."""
    # https://stackoverflow.com/a/65379092
    dd = {}
    for key, val in dinput.items():
        if isinstance(val, dict) and val:
            dd[key] = drop_nones(val)
        elif isinstance(val, (list, set, tuple)):
            # note: Nones in lists are not dropped
            # simply add "if vv is not None" at the end if required

            dd[key] = type(val)(
                drop_nones(vv) if isinstance(vv, dict) else vv for vv in val
            )  # type: ignore
        elif val is not None:
            if isinstance(val, dict) and not val:  # avoid empty {}
                pass
            else:
                dd[key] = val
    return dd


def md5sum(fname: Path) -> str:
    """Calculate the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as fil:
        for chunk in iter(lambda: fil.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def create_symlink(source: str, target: str) -> None:
    """Create a symlinked file with some checks."""

    thesource = Path(source)
    if not thesource.exists():
        raise OSError(f"Cannot symlink: Source file {thesource} does not exist.")

    thetarget = Path(target)

    if thetarget.exists() and not thetarget.is_symlink():
        raise OSError(f"Target file {thetarget} exists already as a normal file.")

    os.symlink(source, target)

    if not (thetarget.exists() and thetarget.is_symlink()):
        raise OSError(f"Target file {thesource} does not exist or is not a symlink.")


def size(fname: str) -> int:
    """Size of file, in bytes"""
    return Path(fname).stat().st_size


def uuid_from_string(string: str) -> uuid.UUID:
    """Produce valid and repeteable UUID4 as a hash of given string"""
    return uuid.UUID(hashlib.md5(string.encode("utf-8")).hexdigest())


def nested_parameters_dict(paramdict: dict[str, str | int | float]) -> types.Parameters:
    """Interpret a flat parameters dictionary into a nested dictionary, based on
    presence of colons in keys.

    This assumes that what comes before a ":" is sort of a namespace identifier.

    In design_kw (semeio) this namespace identifier is actively ignored, meaning that
    the keys without the namespace must be unique.
    """
    nested_dict: types.Parameters = {}
    unique_keys: list[str] = []
    for key, value in paramdict.items():
        if ":" in key:
            subdict, newkey = key.split(":", 1)
            if not newkey:
                raise ValueError(f"Empty parameter name in {key} after removing prefix")
            if subdict not in nested_dict:
                nested_dict[subdict] = {}
            unique_keys.append(newkey)
            nested_dict[subdict][newkey] = value  # type: ignore
        else:
            unique_keys.append(key)
            nested_dict[key] = value

    return nested_dict


def check_if_number(value: str | None) -> int | float | str | None:
    """Check if value (str) looks like a number and return the converted value."""

    if value is None:
        return None

    with contextlib.suppress(ValueError):
        return int(value)

    with contextlib.suppress(ValueError):
        return float(value)

    return value


def get_object_name(obj: Path) -> str | None:
    """Get the name of the object.

    If not possible, return None.
    If result is 'unknown', return None (XTgeo defaults)
    If object is a polygon, and object name is 'poly', return None (XTgeo defaults)
    If object is a grid, and object name is 'noname', return None (XTgeo defaults)

    """

    logger.debug("Getting name from the data object itself")

    try:
        name = obj.name
    except AttributeError:
        logger.info("display.name could not be set")
        return None

    if isinstance(obj, xtgeo.RegularSurface) and name == "unknown":
        logger.debug("Got 'unknown' as name from a surface object, returning None")
        return None

    if isinstance(obj, xtgeo.Polygons) and name == "poly":
        logger.debug("Got 'poly' as name from a polygons object, returning None")
        return None

    if isinstance(obj, xtgeo.Grid) and name == "noname":
        logger.debug("Got 'noname' as name from grids object, returning None")
        return None

    return name


def prettyprint_dict(inp: dict) -> str:
    """Prettyprint a dict into as string variable (for python logging e.g)"""
    return str(json.dumps(inp, indent=2, default=str, ensure_ascii=False))


def some_config_from_env(envvar: str = "FMU_GLOBAL_CONFIG") -> dict | None:
    """Get the config from environment variable.

    This function is only called if config SHALL be fetched from the environment
    variable.
    """

    logger.info("Getting config from file via environment %s", envvar)
    try:
        return ut.yaml_load(os.environ[envvar], loader="fmu")
    except KeyError:
        return None
    except Exception as e:
        raise ValueError(
            "Not able to load config from environment variable "
            f"{envvar} = {os.environ[envvar]}. "
            f"The environment variable {envvar} must point to a valid yaml file."
        ) from e


def read_named_envvar(envvar: str) -> str | None:
    """Read a specific (named) environment variable."""
    return os.environ.get(envvar, None)


def filter_validate_metadata(metadata_in: dict) -> dict:
    """Validate metadatadict at topmost_level and strip away any alien keys."""

    valids = [
        "$schema",
        "version",
        "source",
        "tracklog",
        "class",
        "fmu",
        "file",
        "data",
        "display",
        "access",
        "masterdata",
    ]

    metadata = deepcopy(metadata_in)

    for key in metadata_in:
        if key not in valids:
            del metadata[key]

    return metadata


def generate_description(desc: str | list | None = None) -> list | None:
    """Parse desciption input (generic)."""
    if not desc:
        return None

    if isinstance(desc, str):
        return [desc]
    if isinstance(desc, list):
        return desc

    raise ValueError("Description of wrong type, must be list of strings or string")


def glue_metadata_preprocessed(
    oldmeta: dict[str, Any], newmeta: dict[str, Any]
) -> dict[str, Any]:
    """Glue (combine) to metadata dicts according to rule 'preprocessed'."""

    meta = oldmeta.copy()

    if "_preprocessed" in meta:
        del meta["_preprocessed"]

    meta["fmu"] = newmeta["fmu"]
    meta["file"] = newmeta["file"]

    newmeta["tracklog"][-1]["event"] = "merged"
    meta["tracklog"].extend(newmeta["tracklog"])

    return meta
