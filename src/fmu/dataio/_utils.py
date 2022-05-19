"""Module for private utilities/helpers for DataIO class."""
import hashlib
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd

try:
    import pyarrow as pa
except ImportError:
    HAS_PYARROW = False
else:
    HAS_PYARROW = True
    from pyarrow import feather

import xtgeo
import yaml

from . import _design_kw
from . import _oyaml as oyaml

logger = logging.getLogger(__name__)


def inherit_docstring(inherit_from):
    """Local decorator to inherit a docstring"""

    def decorator_set_docstring(func):
        if func.__doc__ is None and inherit_from.__doc__ is not None:
            func.__doc__ = inherit_from.__doc__
        return func

    return decorator_set_docstring


def detect_inside_rms() -> bool:
    """Detect if 'truly' inside RMS GUI, where predefined variable project exist.

    However this will be overriden by an environment variable for unit testing
    when using the Roxar API python, so that unit test outside of RMS behaves
    properly
    """
    inside_rms = False
    try:
        import roxar

        inside_rms = True
        logger.info("Roxar version is %s", roxar.__version__)
    except ModuleNotFoundError:
        pass

    # a special solution for testing mostly
    if os.environ.get("INSIDE_RMS", 1) == "0":
        inside_rms = False

    logger.info("Running truly in RMS GUI status: %s", inside_rms)
    print(f"\nRunning truly in RMS GUI status: {inside_rms}\n")
    return inside_rms


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
            )
        elif val is not None:
            if isinstance(val, dict) and not val:  # avoid empty {}
                pass
            else:
                dd[key] = val
    return dd


def export_metadata_file(yfile, metadata, savefmt="yaml", verbosity="WARNING") -> None:
    """Export genericly and ordered to the complementary metadata file."""
    logger.setLevel(level=verbosity)
    if metadata:

        xdata = drop_nones(metadata)

        if savefmt == "yaml":
            yamlblock = oyaml.safe_dump(xdata)
            with open(yfile, "w") as stream:
                stream.write(yamlblock)
        else:
            jfile = str(yfile).replace(".yml", ".json")
            jsonblock = json.dumps(xdata, default=str, indent=2)
            with open(jfile, "w") as stream:
                stream.write(jsonblock)

    else:
        raise RuntimeError(
            "Export of metadata was requested, but no metadata are present."
        )
    logger.info("Yaml file on: %s", yfile)


def export_file(obj, filename, extension, flag=None):
    """Export a valid object to file"""
    if extension == ".gri" and isinstance(obj, xtgeo.RegularSurface):
        obj.to_file(filename, fformat="irap_binary")
    elif extension == ".csv" and isinstance(obj, (xtgeo.Polygons, xtgeo.Points)):
        out = obj.copy()  # to not modify incoming instance!
        if "xtgeo" not in flag:
            out.xname = "X"
            out.yname = "Y"
            out.zname = "Z"
            if isinstance(out, xtgeo.Polygons):
                # out.pname = "ID"  not working
                out.dataframe.rename(columns={out.pname: "ID"}, inplace=True)
        out.dataframe.to_csv(filename, index=False)
    elif extension == ".pol" and isinstance(obj, (xtgeo.Polygons, xtgeo.Points)):
        obj.to_file(filename)
    elif extension == ".segy" and isinstance(obj, xtgeo.Cube):
        obj.to_file(filename, fformat="segy")
    elif extension == ".roff" and isinstance(obj, (xtgeo.Grid, xtgeo.GridProperty)):
        obj.to_file(filename, fformat="roff")
    elif extension == ".csv" and isinstance(obj, pd.DataFrame):
        includeindex = True if flag == "include_index" else False
        obj.to_csv(filename, index=includeindex)
    elif extension == ".arrow" and HAS_PYARROW and isinstance(obj, pa.Table):
        # comment taken from equinor/webviz_subsurface/smry2arrow.py

        # Writing here is done through the feather import, but could also be done using
        # pa.RecordBatchFileWriter.write_table() with a few pa.ipc.IpcWriteOptions(). It
        # is convenient to use feather since it has ready configured defaults and the
        # actual file format is the same
        # (https://arrow.apache.org/docs/python/feather.html)
        feather.write_feather(obj, dest=filename)
    else:
        raise TypeError(f"Exporting {extension} for {type(obj)} is not supported")

    return str(filename)


def md5sum(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as fil:
        for chunk in iter(lambda: fil.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def export_file_compute_checksum_md5(obj, filename, extension, flag=None, tmp=False):
    """Export and compute checksum, with possibility to use a tmp file."""

    usefile = filename
    if tmp:
        tmpdir = tempfile.TemporaryDirectory()
        usefile = Path(tmpdir.name) / "tmpfile"

    export_file(obj, usefile, extension, flag=flag)
    checksum = md5sum(usefile)
    if tmp:
        tmpdir.cleanup()
        usefile = None
    return usefile, checksum


def size(fname):
    return Path(fname).stat().st_size


def uuid_from_string(string):
    """Produce valid and repeteable UUID4 as a hash of given string"""
    return uuid.UUID(hashlib.md5(string.encode("utf-8")).hexdigest())


def read_parameters_txt(pfile: Union[Path, str]) -> Dict[str, Union[str, float, int]]:
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


def nested_parameters_dict(
    paramdict: Dict[str, Union[str, int, float]]
) -> Dict[str, Union[str, int, float, Dict[str, Union[str, int, float]]]]:
    """Interpret a flat parameters dictionary into a nested dictionary, based on
    presence of colons in keys.

    This assumes that what comes before a ":" is sort of a namespace identifier.

    In design_kw (semeio) this namespace identifier is actively ignored, meaning that
    the keys without the namespace must be unique.
    """
    nested_dict: Dict[
        str, Union[str, int, float, Dict[str, Union[str, int, float]]]
    ] = {}
    unique_keys: List[str] = []
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


def check_if_number(value):
    """Check if value (str) looks like a number and return the converted value."""

    res = None
    try:
        res = int(value)
    except ValueError:
        try:
            res = float(value)
        except ValueError:
            pass

    if res is not None:
        return res

    return value


def get_object_name(obj):
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
        return

    if isinstance(obj, xtgeo.RegularSurface) and name == "unknown":
        logger.debug("Got 'unknown' as name from a surface object, returning None")
        return

    if isinstance(obj, xtgeo.Polygons) and name == "poly":
        logger.debug("Got 'poly' as name from a polygons object, returning None")
        return

    if isinstance(obj, xtgeo.Grid) and name == "noname":
        logger.debug("Got 'noname' as name from grids object, returning None")
        return

    return name


def prettyprint_dict(inp: dict) -> str:
    """Prettyprint a dict into as string variable (for python logging e.g)"""
    return str(json.dumps(inp, indent=2, default=str))


def some_config_from_env(envvar="FMU_GLOBAL_CONFIG") -> dict:
    """Get the config from environment variable.

    This function is only called if config SHALL be fetched from the environment
    variable: Raise if the environment variable is not found.
    """

    config = None
    logger.info("Getting config from file via environment %s", envvar)
    if envvar in os.environ:
        cfg_path = os.environ[envvar]
    else:
        raise ValueError(
            (
                "No config was received. "
                "The config must be given explicitly as an input argument, or "
                "the environment variable %s must point to a valid yaml file.",
                envvar,
            )
        )

    with open(cfg_path, "r", encoding="utf8") as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            raise

    return config


def load_yaml(yfil: Union[str, Path]) -> dict:
    """Loading a YAML file"""
    cfg = None
    with open(yfil, "r", encoding="UTF8") as stream:
        cfg = yaml.safe_load(stream)
    return cfg
