"""Module for private utilities/helpers for DataIO class."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shlex
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xtgeo
import yaml

from fmu.config import utilities as ut
from fmu.datamodels.fmu_results.data import Geometry

from ._definitions import ERT_RELATIVE_CASE_METADATA_FILE
from ._logging import null_logger
from ._readers.faultroom import FaultRoomSurface

if TYPE_CHECKING:
    from io import BufferedIOBase, BytesIO

    from fmu.dataio.providers.objectdata._base import ObjectDataProvider

    from . import types


logger: Final = null_logger(__name__)


def npfloat_to_float(v: Any) -> Any:
    return float(v) if isinstance(v, np.float64 | np.float32) else v


def dataio_examples() -> bool:
    # This flag is set when the `run-exmaples.sh` script runs.
    return "RUN_DATAIO_EXAMPLES" in os.environ


def export_metadata_file(file: Path, metadata: dict) -> None:
    """Export genericly and ordered to the complementary metadata file."""
    if not metadata:
        raise RuntimeError(
            "Export of metadata was requested, but no metadata are present."
        )

    with open(file, "w", encoding="utf8") as stream:
        stream.write(
            yaml.safe_dump(
                metadata,
                allow_unicode=True,
            )
        )

    logger.info("Yaml file on: %s", file)


def casepath_has_metadata(casepath: Path) -> bool:
    """Check if a proposed casepath has a metadata file"""
    if (casepath / ERT_RELATIVE_CASE_METADATA_FILE).exists():
        logger.debug("Found metadata for proposed casepath <%s>", casepath)
        return True
    logger.debug("Did not find metadata for proposed casepath <%s>", casepath)
    return False


def export_object_to_file(
    file: Path | BytesIO,
    object_export_function: Callable[[Path | BytesIO], None],
) -> None:
    """
    Export a object to file or memory buffer using a provided export function.
    """

    if isinstance(file, Path):
        file.parent.mkdir(parents=True, exist_ok=True)

    object_export_function(file)


# TODO: Remove this function when AggregatedData.export() is removed
def export_file(
    obj: types.Inferrable,
    file: Path | BytesIO,
    file_suffix: str | None = None,
    fmt: str = "",
) -> None:
    """
    Export a valid object to file or memory buffer. If xtgeo is in the fmt string,
    xtgeo xyz-column names will be preserved for xtgeo.Points and xtgeo.Polygons
    """

    if isinstance(file, Path):
        # create output folder if not existing
        file.parent.mkdir(parents=True, exist_ok=True)
        file_suffix = file.suffix

    elif not file_suffix:
        raise ValueError("'suffix' must be provided when file is a BytesIO object")

    if file_suffix == ".gri" and isinstance(obj, xtgeo.RegularSurface):
        obj.to_file(file, fformat="irap_binary")
    elif file_suffix == ".csv" and isinstance(obj, xtgeo.Polygons | xtgeo.Points):
        out = obj.copy()  # to not modify incoming instance!
        if "xtgeo" not in fmt:
            out.xname = "X"
            out.yname = "Y"
            out.zname = "Z"
            if isinstance(out, xtgeo.Polygons):
                # out.pname = "ID"  not working
                out.get_dataframe(copy=False).rename(
                    columns={out.pname: "ID"},
                    inplace=True,  # noqa: PD002
                )
        out.get_dataframe(copy=False).to_csv(file, index=False)
    elif file_suffix == ".pol" and isinstance(obj, xtgeo.Polygons | xtgeo.Points):
        obj.to_file(file)
    elif file_suffix == ".segy" and isinstance(obj, xtgeo.Cube):
        obj.to_file(file, fformat="segy")
    elif file_suffix == ".roff" and isinstance(obj, xtgeo.Grid | xtgeo.GridProperty):
        obj.to_file(file, fformat="roff")
    elif file_suffix == ".csv" and isinstance(obj, pd.DataFrame):
        logger.info(
            "Exporting dataframe to csv. Note: index columns will not be "
            "preserved unless calling 'reset_index()' on the dataframe."
        )
        obj.to_csv(file, index=False)
    elif file_suffix == ".parquet":
        if isinstance(obj, pa.Table):
            pq.write_table(obj, where=pa.output_stream(file))

    elif file_suffix == ".json":
        if isinstance(obj, FaultRoomSurface):
            serialized_json = json.dumps(obj.storage, indent=4)
        else:
            serialized_json = json.dumps(obj)

        if isinstance(file, Path):
            with open(file, "w", encoding="utf-8") as stream:
                stream.write(serialized_json)
        else:
            file.write(serialized_json.encode("utf-8"))

    else:
        raise TypeError(f"Exporting {file_suffix} for {type(obj)} is not supported")


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
      RMS_SEED 1000
      KVKH_CHANNEL 0.6
      GLOBVAR:VOLON_FLOODPLAIN_VOLFRAC 0.256355
      GLOBVAR:VOLON_PERMH_CHANNEL 1100
      LOG10_GLOBVAR:FAULT_SEAL_SCALING 0.685516
      LOG10_MULTREGT:MULT_THERYS_VOLON -3.21365
    """

    logger.debug("Reading parameters.txt from %s", pfile)

    res: types.Parameters = {}

    with open(pfile, encoding="utf-8") as f:
        for line in f:
            line_parts = shlex.split(line)
            if len(line_parts) == 2:
                key, value = line_parts
                res[key] = check_if_number(value)
            else:
                raise ValueError(
                    "The parameters.txt file can only contain two elements per line."
                    f"Found more or less than two on line {line}."
                )

    return res


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
    with open(metafilepath, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def get_geometry_ref(geometrypath: Path, obj: Any) -> Geometry | None:
    """Get a reference to a geometry.

    Read the metadata file for an already exported file, and returns info like this
    for the data block:

    data:
      geometry:
        name: somename
        relative_path: some_relative/path/geometry.roff

    This means that the geometry may be 'located' both on disk (relative path) and in
    Sumo
    """

    if not geometrypath.exists():
        raise FileNotFoundError(
            f"The 'geometry'={geometrypath} is not a path to an existing file. "
            "Ensure it points to an exported grid object."
        )
    try:
        gmeta = read_metadata_from_file(geometrypath)
    except OSError as err:
        raise FileNotFoundError(
            f"Could not detect a metadata file for 'geometry'='{geometrypath}'. "
        ) from err

    # some basic checks (may be exteneded to e.g. match on NCOL, NROW, ...?)
    if isinstance(obj, xtgeo.GridProperty) and gmeta["class"] != "cpgrid":
        raise ValueError("The geometry for a grid property must be a grid")

    if isinstance(obj, xtgeo.RegularSurface) and gmeta["class"] != "surface":
        raise ValueError("The geometry for a surface must be another surface")

    geom_name = gmeta["data"].get("name", "")
    relpath = gmeta["file"]["relative_path"]

    return Geometry(name=geom_name, relative_path=relpath)


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


def convert_datestr_to_isoformat(value: str, format: str = "%Y%m%d") -> str:
    """Convert a date string to ISO formatted string"""
    return datetime.strptime(value, format).isoformat()
