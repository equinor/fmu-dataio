"""Module for private utilities/helpers for DataIO class."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def construct_filename(
    name, hashsign, descr=None, t1=None, t2=None, fmu=1, loc="surface"
):
    """Construct filename stem according to datatype (class) and fmu style.

    fmu style 1:

        surface:
            namehorizon--description--<hash>
            namehorizon--description--t1--<hash>
            namehorizon--description--t2_t1--<hash>

            e.g.
            topvolantis--ds_gf_extracted--<hash>
            therys--facies_fraction_lowershoreface--<hash>

        grid (geometry):
            gridname--<hash>

        gridproperty
            gridname--propdescription--<hash>
            gridname--description--t1--<hash>
            gridname--description--t2_t1--<hash>

            e.g.
            geogrid_valysar--phit--<hash>

    Destinations accoring to datatype

    Returns stem for file name and destination
    """

    stem = "unset"
    dest = "."

    if fmu == 1:
        stem = name.lower()

        if descr:
            stem += "--" + descr.lower()

        if t1 and not t2:
            stem += "--" + t1.lower()

        elif t1 and t2:
            stem += "--" + t2.lower + "_" + t1.lower()

        if loc == "surface":
            dest = "../../share/results/maps"

        elif loc == "grid":
            dest = "../../share/results/grid"

        stem += "--" + hashsign

    return stem, dest


def verify_path(createfolder, filedest, filename, ext):
    path = (Path(filedest) / filename.lower()).with_suffix(ext)

    if path.parent.exists():
        logger.info("Folder exists")
    else:
        if createfolder:
            logger.info("No such folder, will create")
            path.parent.mkdir()
        else:
            raise IOError(f"Folder {str(path.parent)} is not present.")

    return path
