"""Module for private utilities/helpers for DataIO class."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import yaml

from fmu.config import utilities as ut

from ._definitions import ERT_RELATIVE_CASE_METADATA_FILE
from ._logging import null_logger

if TYPE_CHECKING:
    from io import BufferedIOBase, BytesIO

    from fmu.dataio.providers.objectdata._base import ObjectDataProvider

    from . import types


logger: Final = null_logger(__name__)


def casepath_has_metadata(casepath: Path) -> bool:
    """Check if a proposed casepath has a metadata file"""
    if (casepath / ERT_RELATIVE_CASE_METADATA_FILE).exists():
        logger.debug("Found metadata for proposed casepath <%s>", casepath)
        return True
    logger.debug("Did not find metadata for proposed casepath <%s>", casepath)
    return False


def md5sum(file: Path | BytesIO) -> str:
    if isinstance(file, Path):
        with open(file, "rb") as stream:
            return md5sum_stream(stream)
    return md5sum_stream(file)


def md5sum_stream(stream: BufferedIOBase) -> str:
    """Calculate the MD5 checksum of a stream."""
    stream.seek(0)

    hash_md5 = hashlib.md5()
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def compute_md5_and_size_from_objdata(objdata: ObjectDataProvider) -> tuple[str, int]:
    """Compute an MD5 sum for an object."""
    try:
        return objdata.compute_md5_and_size()
    except Exception as e:
        logger.debug(
            f"Exception {e} occured when trying to compute md5 from memory stream "
            f"for an object of type {type(objdata.obj)}. Will use tempfile instead."
        )
        return objdata.compute_md5_and_size_using_temp_file()


def uuid_from_string(string: str) -> uuid.UUID:
    """Produce valid and repeteable UUID4 as a hash of given string"""
    return uuid.UUID(hashlib.md5(string.encode("utf-8")).hexdigest())


def read_parameters_txt(pfile: Path | str) -> types.Parameters:
    """Read the parameters.txt file and convert to a dict.
    The parameters.txt file has this structure::
      RMS_SEED 1000
      KVKH_CHANNEL 0.6
      GLOBVAR:VOLON_FLOODPLAIN_VOLFRAC 0.256355
      GLOBVAR:VOLON_PERMH_CHANNEL 1100
      LOG10_GLOBVAR:FAULT_SEAL_SCALING 0.685516
      LOG10_MULTREGT:MULT_THERYS_VOLON -3.21365
    """

    logger.debug("Reading parameters.txt from %s", pfile)

    res: types.Parameters = {}

    def parse_value(value: str | None) -> int | float | str | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    with open(pfile, encoding="utf-8") as f:
        for line in f:
            line_parts = shlex.split(line)
            if len(line_parts) == 2:
                key, value = line_parts
                res[key] = parse_value(value)
            else:
                raise ValueError(
                    "The parameters.txt file can only contain two elements per line."
                    f"Found more or less than two on line {line}."
                )

    return res


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
    with open(metafilepath, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def load_config_from_path(config_path: Path) -> dict[str, Any]:
    """Retrieve the global config data by reading the global config file."""
    logger.debug("Set global config...")

    if not isinstance(config_path, Path):
        raise ValueError("The config_path argument needs to be a path")

    if not config_path.is_file():
        raise FileNotFoundError(f"Cannot find file for global config: {config_path}")

    config = ut.yaml_load(config_path)
    if not config:
        # This should never happen because we don't provide tool=.. to yaml_load.
        raise RuntimeError(
            f"Attempted to use unknown tool when loading config: {config_path}"
        )

    return config
