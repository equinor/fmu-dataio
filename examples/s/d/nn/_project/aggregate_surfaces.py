"""Use fmu-dataio for aggregated surfaces created by an aggregation service."""

from pathlib import Path
import logging

import yaml
import numpy as np

import xtgeo
import fmu.dataio


def main():
    """Aggregate one surface across X realizations from the example case and store the
    results. In this example, we emulate that fmu-dataio is called by another service.

    Two contexts are demonstrated:

        1) We are in a classical FMU setting, running this aggregation as a stand-alone
           Python script (directly, or wrapped in an ERT workflow). In this context,
           we want the resulting files to be stored to disk within the existing case. In
           this context, fmu-dataio is responsible for storing the results.
        2) We are in a cloud service. In this context, we don't want to store anything
           on disk, as the results are to be pushed to other storage, i.e. Sumo. Hence,
           we want fmu-dataio to provide us with the generated metadata only. In this
           context, the service itself is responsible for storing the results.

    Note that this example is showing the usage of fmu-dataio, it is not to be seen as
    an example for the actual aggregation. The aggregation service shown here is
    simplistic and its sole purpose is to facilitate the fmu-dataio example.

    """

    # First we get the input data (the individual surfaces from each realization), which
    # we assume are stored in classical FMU style on /scratch disk folder structure.

    # IRL, these variables would typically be arguments to the aggregation script.
    casepath = Path("../xcase/").resolve()
    iter_name = "iter-0"
    relative_path = (
        "share/results/maps/topvolantis--ds_extract_geogrid.gri"  # exists in all reals
    )
    realization_ids = _get_realization_ids(casepath)

    # gather source surfaces and their associated metadata
    source_surfaces, source_metadata = _get_source_surfaces_from_disk(
        casepath=casepath,
        iter_name=iter_name,
        realization_ids=realization_ids,
        relative_path=relative_path,
    )

    # These are the operations we want to do
    operations = ["mean", "min", "max", "std"]

    # This is the ID we assign to this set of aggregations
    aggregation_id = "something_very_unique"  # IRL this will usually be a uuid

    # We aggregate these source surfaces and collect results in list of dictionaries
    aggregations = []

    # Initialize an AggregatedData object for this set of aggregations
    exp = fmu.dataio.AggregatedData(
        source_metadata=source_metadata,
        aggregation_id=aggregation_id,
        casepath=casepath,
    )

    for operation in operations:

        print(f"Running aggregation: {operation}")

        # Call the aggregation machine and create an aggregated surface
        # Note that this is not part of fmu-dataio - it is merely a mock-up
        # aggregation service for the sake of this example.
        aggregated_surface = _aggregate(source_surfaces, operation)

        # ==============================================================================
        # Example 1: We want fmu-dataio to export the file + metadata to disk
        saved_filename = exp.export(aggregated_surface, operation=operation)
        print(f"Example 1: File saved to {saved_filename}")

        # ==============================================================================
        # Example 2: We only want the metadata (e.g. we are in a cloud service)
        metadata = exp.generate_metadata(aggregated_surface, operation=operation)
        print(f"Example 2: Metadata generated")

        # At this point, we have the surface, the operation and the metadata
        # These can be collected into e.g. a list or a dictionary for further usage,
        # or we can upload to Sumo as part of the loop.


# ======================================================================================
# This concludes the main examples. Below are utility functions used by the example.
# ======================================================================================


def _aggregate(source_surfaces, operation):
    """Aggregate a set of surfaces, return the result.

    This is a very simplistic and minimalistic aggregation method meant to power this
    example only. Do not use in production setting.
    """

    if operation == "mean":
        return source_surfaces.apply(np.nanmean, axis=0)
    if operation == "min":
        return source_surfaces.apply(np.min, axis=0)
    if operation == "max":
        return source_surfaces.apply(np.max, axis=0)
    if operation == "std":
        return source_surfaces.apply(np.std, axis=0)

    # In a real aggregation service, more options would of course be supported. However,
    # in this example, we do not include anything beyond the basics.

    raise NotImplementedError(
        f"Aggregation method {operation} is not implemented in this example."
    )


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


def _get_realization_ids(casepath):
    """Given a path to a case on the disk, get the individual realizations."""

    # In reality we would traverse the disk to find out, use Sumo search, or preferably
    # ask ERT for it. For the sake of the example we just hardcode it here.

    return [0, 1, 9]


def _get_source_surfaces_from_disk(
    casepath: Path, iter_name: str, realization_ids: list, relative_path: Path
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

    for real in realization_ids:
        surfacepath = casepath / f"realization-{real}" / iter_name / relative_path
        surface = xtgeo.surface_from_file(surfacepath)
        metadata = fmu.dataio.read_metadata(surfacepath)

        # this example is minimalistic and super non-robust. In reality, there will
        # be realizations missing which needs to be handled etc.

        collected_data.append((surface, metadata))

    source_surfaces = xtgeo.Surfaces([surface for surface, _ in collected_data])
    source_metadata = [metadata for _, metadata in collected_data]

    return source_surfaces, source_metadata


def _get_source_surfaces_from_sumo(
    case_uuid: str, iter_name: str, realization_ids: list, relative_path: Path
):
    """Collect surfaces and metadata from Sumo.

    Placeholder for a method getting surfaces and metadata from Sumo, complementing
    the similar method for getting this from the disk. Only included since it is
    referenced in the comments in main().

    Not implemented.
    """
    raise NotImplementedError()


if __name__ == "__main__":
    main()
