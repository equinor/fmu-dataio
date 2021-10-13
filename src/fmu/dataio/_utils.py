"""Module for private utilities/helpers for DataIO class."""
import hashlib
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Union

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


def drop_nones(dinput: dict) -> dict:
    """Recursively drop Nones in dict dinput and return a new dict."""
    # https://stackoverflow.com/a/65379092
    dd = {}
    for key, val in dinput.items():
        if isinstance(val, dict):
            dd[key] = drop_nones(val)
        elif isinstance(val, (list, set, tuple)):
            # note: Nones in lists are not dropped
            # simply add "if vv is not None" at the end if required
            dd[key] = type(val)(
                drop_nones(vv) if isinstance(vv, dict) else vv for vv in val
            )
        elif val is not None:
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


def md5sum(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as fil:
        for chunk in iter(lambda: fil.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


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

    if len(unique_keys) > len(set(unique_keys)):
        raise ValueError(
            "Keys in parameters dictionary are not unique after removal of namespace"
        )

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
