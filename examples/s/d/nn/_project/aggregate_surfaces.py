"""Example script for using fmu-dataio to attach metadata to aggregated surfaces
created by an aggregation service."""

from pathlib import Path
import logging

import yaml
import numpy as np

import xtgeo
import fmu.dataio


def main():
    """Aggregate one surface across X realizations from the example case and create
    metadata for it without exporting.

    In this example, we emulate that fmu-dataio is called by another service to produce
    the metadata. Therefore, fmu-dataio will in this example not export any files or
    metadata to disk or elsewhere. The aggregation service passes the aggregated service
    throughfmu-dataio, and fmu-dataio returns the generated metadata as a dictionary.

    In this example, the aggregation service will be responsible for the aggregation,
    and for storing the resulting file with associated metadata.
    """

    # Note that this is a simplified and minimalistic example of an aggregation script
    # which sole purpose is to facilitate the fmu-dataio example. This is not an example
    # of an aggregation method - it is an example of how fmu-dataio can be used in such
    # a setting.

    # get the input realisations (the individual surfaces within each realization)

    # Context 1: Surfaces are stored on /scratch disk folder structure
    casepath = Path("../xcase/").resolve()
    iter_name = "iter-0"
    relative_path = (
        "share/results/maps/topvolantis--ds_extract_geogrid.gri"  # exists in all reals
    )
    realization_ids = _get_realization_ids(casepath)

    # In this simplified example, we assume that we know the surface name.
    # Usually, this would be derived from a wildcard search on realization-0 or similar.
    # The point is that each realization contains a representation of the same surface
    # and it has the same filename across all realizations.

    # gather source surfaces and their associated metadata
    source_surfaces, source_metadata = _get_source_surfaces_from_disk(
        casepath=casepath,
        iter_name=iter_name,
        realization_ids=realization_ids,
        relative_path=relative_path,
    )

    # Context 2: If surfaces are stored in cloud storage, i.e. Sumo or similar, the
    # process of getting them will be slightly different. We emulate this here for the
    # sake of the example, but this has not been implemented.

    #! source_surfaces, source_metadata = _get_source_surfaces_from_sumo(
    #!  case_uuid=case_uuid,
    #!  iter_name=iter_name,
    #!  realization_ids=realization_ids,
    #!  relative_path=relative_path
    #!)

    # (This example will continue with surfaces from disk.)

    # These are the operations we want to do
    operations = ["mean", "min", "max", "std"]

    # This is the ID we assign to this set of aggregations
    aggregation_id = "something_very_unique"  # IRL this will usually be a uuid

    # We aggregate these source surfaces and collect results in list of dictionaries
    aggregations = []
    for operation in operations:

        # Call the aggregation machine and create an aggregated surface
        surface = _aggregate(source_surfaces, operation)

        # Call fmu-dataio and create metadata for the aggregated surface
        # fmu.dataio.ExportAggregatedData is initialized once for each aggregations set.

        # ==============================================================================
        # Example 1: We want fmu-dataio to export the file + metadata to disk
        exp = fmu.dataio.ExportAggregatedData(
            source_metadata=source_metadata,
            aggregation_id=aggregation_id,
        )
        saved_filename = exp.export(surface, casepath=casepath, operation=operation)

        print(f"surface has been saved to {saved_filename}")

        # ==============================================================================
        # Example 2: We only need the metadata
        exp = fmu.dataio.ExportAggregatedData(
            source_metadata=source_metadata,
            aggregation_id=aggregation_id,
        )
        metadata = exp.generate_metadata(surface, operation=operation)

        # At this point, we have the surface, the operation and the metadata
        # These can be collected into e.g. a list or a dictionary for further usage,
        # or we can upload to Sumo (not implemented in this example).

        # For now, we collect them in the 'aggregations' list for sake of the example.
        aggregations.append(
            {
                "surface": surface,
                "operation": operation,
                "metadata": metadata,
            }
        )

    # Now, 'aggregations' is a list of dictionaries where each dict contains one
    # aggregation represented by the actual surface, the operation conducted and the
    # associated metadata. We can now pass this along to where it needs to be.

    # If multiple aggregations are performed in the same go, the list can be put into
    # a dictionary using the aggregation_id as the key. More aggregation sets can then
    # be appended, i.e.:

    all_aggregations = {aggregation_id: aggregations}

    # For sake of the example, printing some info from the results:
    example = all_aggregations[aggregation_id][0]

    print("\nExample results:")
    print(f'The operation: {example["operation"]}')
    print(f'The resulting surface: \n {example["surface"]}')
    print(f'The metadata generated: \n {example["metadata"]}')


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

        metadatapath = _metadata_filename(surfacepath)
        metadata = _parse_yaml(metadatapath)

        # this example is minimalistic and super non-robust. In reality, there will
        # be realizations missing etc which needs to be handled.

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
