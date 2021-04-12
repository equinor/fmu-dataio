"""Module for private utilities/helpers for DataIO class."""
import logging
from pathlib import Path
from collections import OrderedDict
from io import StringIO
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

    stem = "unset"
    dest = Path(".")

    if fmu == 1:
        stem = name.lower()

        if descr:
            stem += "--" + descr.lower()

        if t1 and not t2:
            stem += "--" + str(t1).lower()

        elif t1 and t2:
            stem += "--" + str(t2).lower() + "_" + str(t1).lower()

        if loc == "surface":
            dest = dest / outroot / "maps"
        elif loc == "grid":
            dest = dest / outroot / "grids"
        else:
            dest = dest / outroot / "unknown"

    return stem, dest


def verify_path(createfolder, filedest, filename, ext):
    path = (Path(filedest) / filename.lower()).with_suffix(ext)

    if path.parent.exists():
        logger.info("Folder exists")
    else:
        if createfolder:
            logger.info("No such folder, will create")
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise IOError(f"Folder {str(path.parent)} is not present.")

    # create metafile path
    metapath = (Path(filedest) / "." + filename.lower()).with_suffix("yml")

    return path, metapath


def export_metadata_file(mfile, metadata) -> None:
    """Export genericly the complementary metadata file."""
    # mfile is the _XTGeoFile instance for exporting e.g. a surface

    def _oyamlify(metadatadict) -> str:
        """Process yaml output for ordered dictionaries."""
        #
        def represent_dictionary_order(self, dict_data):
            return self.represent_mapping("tag:yaml.org,2002:map", dict_data.items())

        def setup_yaml():
            yaml.add_representer(OrderedDict, represent_dictionary_order)

        setup_yaml()

        stream = StringIO()
        yaml.dump(metadatadict, stream)
        yamlblock = stream.getvalue()
        stream.close()

        return yamlblock

    yamlbase = mfile.file.stem  # the Path object
    yamlparent = mfile.file.parent
    yamlbase = Path("." + yamlbase).with_suffix(".yml")
    yamlfile = yamlparent / yamlbase

    if metadata:
        oyaml = _oyamlify(metadata)
        with open(yamlfile, "w") as stream:
            stream.write(oyaml)
    else:
        raise RuntimeError(
            "Export of metadata was requested, but no metadata are present."
        )
