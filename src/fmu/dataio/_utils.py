"""Module for private utilities/helpers for DataIO class."""
import logging
from pathlib import Path
import uuid
import hashlib
import json

from . import _oyaml as oyaml

logger = logging.getLogger(__name__)


def construct_filename(
    name,
    tagname=None,
    t1=None,
    t2=None,
    fmu=1,
    outroot="../../share/results/",
    loc="surface",
    verbosity="WARNING",
):
    """Construct filename stem according to datatype (class) and fmu style.

    fmu style 1:

        surface:
            namehorizon--tagname
            namehorizon--tagname--t1
            namehorizon--tagname--t2_t1

            e.g.
            topvolantis--ds_gf_extracted
            therys--facies_fraction_lowershoreface

        grid (geometry):
            gridname--<hash>

        gridproperty
            gridname--proptagname
            gridname--tagname--t1
            gridname--tagname--t2_t1

            e.g.
            geogrid_valysar--phit

    Destinations accoring to datatype

    Returns stem for file name and destination
    """
    logger.setLevel(level=verbosity)

    stem = "unset"

    outroot = Path(outroot)

    if fmu == 1:
        stem = name.lower()

        if tagname:
            stem += "--" + tagname.lower()

        if t1 and not t2:
            stem += "--" + str(t1).lower()

        elif t1 and t2:
            stem += "--" + str(t2).lower() + "_" + str(t1).lower()

        if loc == "surface":
            dest = outroot / "maps"
        elif loc == "grid":
            dest = outroot / "grids"
        elif loc == "table":
            dest = outroot / "tables"
        elif loc == "polygons":
            dest = outroot / "polygons"
        else:
            dest = outroot / "other"

    return stem, dest


def verify_path(createfolder, filedest, filename, ext, verbosity="WARNING"):
    logger.setLevel(level=verbosity)

    path = (Path(filedest) / filename.lower()).with_suffix(ext)
    abspath = path.resolve()

    if path.parent.exists():
        logger.info("Folder exists")
    else:
        if createfolder:
            logger.info("No such folder, will create")
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise IOError(f"Folder {str(path.parent)} is not present.")

    # create metafile path
    metapath = (Path(filedest) / ("." + filename.lower())).with_suffix(".yml")
    relpath = str(path).replace("../", "")

    logger.info("Full path to the actual file is: %s", abspath)
    logger.info("Full path to the metadata file (if used) is: %s", metapath)
    logger.info("Relative path to actual file: %s", relpath)

    return path, metapath, relpath, abspath


def drop_nones(dinput: dict) -> dict:
    """Recursively drop Nones in dict d and return a new dict."""
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


def uuid_from_string(string):
    """Produce valid and repeteable UUID4 as a hash of given string"""
    return uuid.UUID(hashlib.md5(string.encode("utf-8")).hexdigest())
