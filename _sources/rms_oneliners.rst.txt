RMS targeted functions
======================

For lowerering the user threshold, some "one-liner" functions have been made for RMS. The purpose
is both to make it simpler for users to export certain items, and in addition secure a better
consistency. Hence the end user is not burdened to provide details, and only a script with quite
a few lines will be needed.

Currently only volumes are exposed, but this will be extended in the near future.

.. note::
All simplified export functions requires that the global configuration file is found at the standard
location in FMU. For RMS exports that will be ``'../../fmuconfig/output/global_variables.yml'``.

.. _example-export-volumes-rms:

Exporting inplace volumes from RMS
----------------------------------

Inplace volumes for grids in RMS should always be computed in a **single** RMS volumetrics job, and
the result should be stored as a report table inside RMS. The simplified export function will use
the RMS API behind the scene to retrieve this table, and all necessary data needed for ``fmu.dataio``.

The performance of the volumetrics jobs in RMS has greatly improved from the past, now typically
representing the fastest method for calculating in-place volumes. However, it is important to note
that generating output maps, such as Zone maps, during the volumetrics job can significantly
decelerate the process.

Note some assets are using erosion multipliers as a means to reduce the bulk and pore volume, instead of
performing actual erosion by cell removal in the grid. This is not supported, and proper grid erosion
is required. If the erosion multiplier is important for flow simulation, the erosion and volumetrics job
should be moved to after the export for flow simulation.

Example:

.. code-block:: python

    from fmu.dataio.export.rms import export_inplace_volumes
    ...

    # here 'Geogrid' is the grid model name, and 'geogrid_volumes' is the name of the volume job
    export_results = export_inplace_volumes(project, "Geogrid", "geogrid_volumes")

    for result in export_results.items:
        print(f"Output volumes to {result.absolute_path}")



Details
-------

.. automodule:: fmu.dataio.export.rms.inplace_volumes
    :members:
