"""Module for private utilities/helpers for DataIO class."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import uuid
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Final, Literal

import numpy as np
import pandas as pd
import xtgeo
import yaml

from fmu.config import utilities as ut

from . import _design_kw, types
from ._logging import null_logger
from .readers import FaultRoomSurface

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


def export_metadata_file(
    file: Path,
    metadata: dict,
    savefmt: Literal["yaml", "json"] = "yaml",
) -> None:
    """Export genericly and ordered to the complementary metadata file."""
    if not metadata:
        raise RuntimeError(
            "Export of metadata was requested, but no metadata are present."
        )

    if savefmt == "yaml":
        with open(file, "w", encoding="utf8") as stream:
            stream.write(
                yaml.safe_dump(
                    drop_nones(metadata),
                    allow_unicode=True,
                )
            )
    else:
        with open(file.replace(file.with_suffix(".json")), "w") as stream:
            stream.write(
                json.dumps(
                    drop_nones(metadata),
                    default=str,
                    indent=2,
                    ensure_ascii=False,
                )
            )

    logger.info("Yaml file on: %s", file)


def export_file(
    obj: types.Inferrable,
    filename: Path,
    flag: str | None = None,
) -> str:
    """Export a valid object to file"""

    if filename.suffix == ".gri" and isinstance(obj, xtgeo.RegularSurface):
        obj.to_file(filename, fformat="irap_binary")
    elif filename.suffix == ".csv" and isinstance(obj, (xtgeo.Polygons, xtgeo.Points)):
        out = obj.copy()  # to not modify incoming instance!
        assert flag is not None
        if "xtgeo" not in flag:
            out.xname = "X"
            out.yname = "Y"
            out.zname = "Z"
            if isinstance(out, xtgeo.Polygons):
                # out.pname = "ID"  not working
                out.get_dataframe(copy=False).rename(
                    columns={out.pname: "ID"}, inplace=True
                )
        out.get_dataframe(copy=False).to_csv(filename, index=False)
    elif filename.suffix == ".pol" and isinstance(obj, (xtgeo.Polygons, xtgeo.Points)):
        obj.to_file(filename)
    elif filename.suffix == ".segy" and isinstance(obj, xtgeo.Cube):
        obj.to_file(filename, fformat="segy")
    elif filename.suffix == ".roff" and isinstance(
        obj, (xtgeo.Grid, xtgeo.GridProperty)
    ):
        obj.to_file(filename, fformat="roff")
    elif filename.suffix == ".csv" and isinstance(obj, pd.DataFrame):
        logger.info(
            "Exporting dataframe to csv. Note: index columns will not be "
            "preserved unless calling 'reset_index()' on the dataframe."
        )
        obj.to_csv(filename, index=False)
    elif filename.suffix == ".parquet":
        from pyarrow import Table

        if isinstance(obj, Table):
            from pyarrow import parquet

            parquet.write_table(obj, where=str(filename))

    elif filename.suffix == ".json" and isinstance(obj, FaultRoomSurface):
        with open(filename, "w") as stream:
            json.dump(obj.storage, stream, indent=4)
    elif filename.suffix == ".json":
        with open(filename, "w") as stream:
            json.dump(obj, stream)
    else:
        raise TypeError(f"Exporting {filename.suffix} for {type(obj)} is not supported")

    return str(filename)


def md5sum(fname: Path) -> str:
    """Calculate the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as fil:
        for chunk in iter(lambda: fil.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def export_file_compute_checksum_md5(
    obj: types.Inferrable,
    filename: Path,
    flag: str | None = None,
) -> str:
    """Export and compute checksum"""
    export_file(obj, filename, flag=flag)
    return md5sum(filename)


def compute_md5_using_temp_file(
    obj: types.Inferrable, extension: str, flag: str = ""
) -> str:
    """Compute an MD5 sum using a temporary file."""
    if not extension.startswith("."):
        raise ValueError("An extension must start with '.'")

    with NamedTemporaryFile(buffering=0, suffix=extension) as tf:
        logger.info("Compute MD5 sum for tmp file...: %s", tf.name)
        return export_file_compute_checksum_md5(
            obj=obj, filename=Path(tf.name), flag=flag
        )


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


def read_parameters_txt(pfile: Path | str) -> types.Parameters:
    """Read the parameters.txt file and convert to a dict.
    The parameters.txt file has this structure::
      SENSNAME rms_seed
      SENSCASE p10_p90
      RMS_SEED 1000
      KVKH_CHANNEL 0.6
      KVKH_CREVASSE 0.3
      GLOBVAR:VOLON_FLOODPLAIN_VOLFRAC 0.256355
      GLOBVAR:VOLON_PERMH_CHANNEL 1100
      GLOBVAR:VOLON_PORO_CHANNEL 0.2
      LOG10_GLOBVAR:FAULT_SEAL_SCALING 0.685516
      LOG10_MULTREGT:MULT_THERYS_VOLON -3.21365
      LOG10_MULTREGT:MULT_VALYSAR_THERYS -3.2582
    ...but may also appear on a justified format, with leading
    whitespace and tab-justified columns, legacy from earlier
    versions but kept alive by some users::
                            SENSNAME     rms_seed
                            SENSCASE     p10_p90
                            RMS_SEED     1000
                        KVKH_CHANNEL     0.6
          GLOBVAR:VOLON_PERMH_CHANNEL    1100
      LOG10_GLOBVAR:FAULT_SEAL_SCALING   0.685516
      LOG10_MULTREGT:MULT_THERYS_VOLON   -3.21365
    This should be parsed as::
        {
        "SENSNAME": "rms_seed"
        "SENSCASE": "p10_p90"
        "RMS_SEED": 1000
        "KVKH_CHANNEL": 0.6
        "KVKH_CREVASSE": 0.3
        "GLOBVAR": {"VOLON_FLOODPLAIN_VOLFRAC": 0.256355, ...etc}
        }
    """

    logger.debug("Reading parameters.txt from %s", pfile)

    parameterlines = Path(pfile).read_text().splitlines()

    dict_str_to_str = _design_kw.extract_key_value(parameterlines)
    return {key: check_if_number(value) for key, value in dict_str_to_str.items()}


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


def read_metadata_from_file(filename: str | Path) -> dict:
    """Read the metadata as a dictionary given a filename.

    If the filename is e.g. /some/path/mymap.gri, the assosiated metafile
    will be /some/path/.mymap.gri.yml (or json?)

    Args:
        filename: The full path filename to the data-object.

    Returns:
        A dictionary with metadata read from the assiated metadata file.
    """
    fname = Path(filename)
    if fname.stem.startswith("."):
        raise OSError(f"The input is a hidden file, cannot continue: {fname.stem}")

    metafile = str(fname.parent) + "/." + fname.stem + fname.suffix + ".yml"
    metafilepath = Path(metafile)
    if not metafilepath.exists():
        raise OSError(f"Cannot find requested metafile: {metafile}")
    with open(metafilepath) as stream:
        return yaml.safe_load(stream)
