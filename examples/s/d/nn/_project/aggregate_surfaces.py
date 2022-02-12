"""Example script emulating a function for aggregating surfaces.

In FMU level 5 usage, many realisations of the same data object (e.g. a surface) is
produced. Individual realisations will, on their own, not adequately represent results
from such an uncertainty-centric run. Therefore, to communicate, compare, visualize 
such results they are aggregated.

For surfaces, results are typically new surfaces representing point-wise statistics of
the input realisations.

E.g. mean(real1/mysurface, real2/mysurface, ..., realn/mysurface) = meansurface

This example showcases how fmu dataio can be used to
1) Produce metadata for an existing aggregated surface, or
2) Produce metadata + export as file an aggregated surface.

...in two different contexts:
1) Realisations are store on the disk (aka scratch disk pattern)
2) Realisations are stored in the cloud (aka Sumo pattern)

Aggregations differ a bit from realizations in the sense that they take much of their
features and properties from the input surfaces. In fmu-dataio, the first instance in
the given list of source metadata will be used as a template.

"""

from pathlib import Path
import yaml

import numpy as np

import xtgeo
import fmu.dataio


def _parse_yaml(fname):
    """Parse the yaml-file, return dict.

    Args:
        fname (Path): Absolute path to yaml file.
    Returns:
        dict
    """

    with open(fname, "r") as stream:
        data = yaml.safe_load(stream)
    return data


def _metadata_filename(fname):
    """From a regular filename, derive the corresponding metadata filename.

    FMU standard: metadata filename = /path/.<stem.ext>.yml

    """

    return Path(fname.parent, "." + fname.name + ".yml")


def _get_realizations(casepath):
    """Given a path to a case on the disk, get the individual realizations."""

    # Ideally we get this from ERT or traverse the disk to find out. For the sake of the
    # example we just hardcode it here.

    return [0, 1, 9]


def _get_source_surfaces_from_disk(
    casepath: Path, iter_name: str, reals: list, relative_path: Path
):
    """Collect surfaces and metadata from disk.

    This method collects the source surfaces from disk. Source surfaces are the
    individual realization surfaces which shall be aggregated.

    A similar method will exist for other sources than /scratch, e.g. Sumo.

    Args:
        casepath (Path): Absolute path to the case root.
        iter_name (str): Name of the iteration (folder), e.g. "iter-0"
        reals (list of ids): List of realization-ids, e.g. 0,1,2,3
        relative_path (Path): Relative path below ERT RUNPATH to the surface


    By combining the casepath and the relative path, parse the surfaces and metadata
    and return surfaces as an xtgeo.Surfaces object and the metadata as a list of dicts.

    """

    collected_data = []

    for r in reals:
        surfacepath = casepath / f"realization-{r}" / iter_name / relative_path
        surface = xtgeo.surface_from_file(surfacepath)

        metadatapath = _metadata_filename(surfacepath)
        metadata = _parse_yaml(metadatapath)

        # this example is minimalistic and super non-robust. In reality, there will
        # be realizations missing etc which needs to be handled.

        collected_data.append((surface, metadata))

    source_surfaces = xtgeo.Surfaces([surface for surface, _ in collected_data])
    source_metadata = [metadata for _, metadata in collected_data]

    return source_surfaces, source_metadata


def main():
    """Aggregate one surface across X realizations from the example case."""

    # get the input realisations
    casepath = Path("examples/s/d/nn/xcase/").resolve()

    # Assuming that we know the surface name here.
    # Usually, this would be derived from a wildcard search on realization-0 or similar
    # The point is that each realization contains a representation of the same surface
    # and it has the same filename across all realizations.

    iter_name = "iter-0"
    relative_path = (
        "share/results/maps/topvolantis--ds_extract_geogrid.gri"  # exists in all reals
    )

    reals = _get_realizations(casepath)

    # gather source surfaces and their associated metadata
    source_surfaces, source_metadata = _get_source_surfaces_from_disk(
        casepath=casepath, iter_name=iter_name, reals=reals, relative_path=relative_path
    )

    # Initialize a dictionary in which we will gather all the results
    aggregations = {
        "mean": {
            "operation": "mean",
            "surface": source_surfaces.apply(np.nanmean, axis=0),
        },
        "min": {"operation": "min", "surface": source_surfaces.apply(np.min, axis=0)},
        "max": {"operation": "max", "surface": source_surfaces.apply(np.max, axis=0)},
        "std": {
            "operation": "std",
            "surface": source_surfaces.apply(np.std, axis=0),
        }
        # percentiles are time-consuming to do directly, so need separate functions
        # for this which is currently not included in the example. #TODO
    }

    # now populate with metadata
    for agg in aggregations:
        aggregation = aggregations[agg]
        operation = aggregation["operation"]
        surface = aggregation["surface"]
        aggregation_id = "0000-0000"  # an identifier for these aggregations

        # TODO: Check if surfaces are re-calculated here...

        exp = fmu.dataio.ExportAggregatedData(
            source_metadata=source_metadata,  # list of metadata for the surfaces used
            aggregation_id=aggregation_id,
            verbosity="DEBUG",
        )
        # We generate metadata and store in the dictionary for later usage
        metadata = exp.generate_metadata(obj=surface, operation=operation)
        aggregation["metadata"] = metadata

    # End result is a dictionary populated with aggregated surfaces + metadata
    # Now we can do whatever we want with these. They can go to a visualization
    # service, a cloud storage or a disk storage.

    # ==================================================================================

    # Example II: In the case where we want them to be stored to the /scratch disk,
    # we can do this with fmu.dataio directly

    for agg in aggregations:
        aggregation = aggregations[agg]
        operation = aggregation["operation"]
        surface = aggregation["surface"]
        aggregation_id = "0000-0000"  # an identifier for these aggregations

        exp = fmu.dataio.ExportAggregatedData(
            source_metadata=source_metadata,
            aggregation_id=aggregation_id,
            verbosity="DEBUG",
        )
        # We export the surface + metadata to disk
        savedpath = exp.export(obj=surface, operation=operation, casepath=casepath)

        print(f"surface has been saved: {savedpath}")


if __name__ == "__main__":
    main()
