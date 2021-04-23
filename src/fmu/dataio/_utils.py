"""Module for private utilities/helpers for DataIO class."""
import logging
from pathlib import Path
from collections import OrderedDict
from io import StringIO
import hashlib
import json

import yaml

logger = logging.getLogger(__name__)


def construct_filename(
    name,
    descr=None,
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
            namehorizon--description
            namehorizon--description--t1
            namehorizon--description--t2_t1

            e.g.
            topvolantis--ds_gf_extracted
            therys--facies_fraction_lowershoreface

        grid (geometry):
            gridname--<hash>

        gridproperty
            gridname--propdescription
            gridname--description--t1
            gridname--description--t2_t1

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

        if descr:
            stem += "--" + descr.lower()

        if t1 and not t2:
            stem += "--" + str(t1).lower()

        elif t1 and t2:
            stem += "--" + str(t2).lower() + "_" + str(t1).lower()

        if loc == "surface":
            dest = outroot / "maps"
        elif loc == "grid":
            dest = outroot / "grids"
        else:
            dest = outroot / "unknown"

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


def export_metadata_file(yfile, metadata) -> None:
    """Export genericly the complementary metadata file."""

    def _oyamlify(metadatadict) -> str:
        """Process yaml output for ordered dictionaries."""
        #
        def represent_dictionary_order(self, dict_data):
            return self.represent_mapping("tag:yaml.org,2002:map", dict_data.items())

        def setup_yaml():
            yaml.add_representer(OrderedDict, represent_dictionary_order)

        setup_yaml()

        stream = StringIO()
        metadatadict = json.loads(json.dumps(metadatadict, default=str))
        yaml.safe_dump(metadatadict, stream)
        yamlblock = stream.getvalue()
        stream.close()

        return yamlblock

    if metadata:
        yamlblock = _oyamlify(metadata)
        with open(yfile, "w") as stream:
            stream.write(yamlblock)
    else:
        raise RuntimeError(
            "Export of metadata was requested, but no metadata are present."
        )


def md5sum(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
