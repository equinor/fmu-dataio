RMS targeted functions
======================

For lowerering the user threshold, some "one-liner" functions have been made for RMS. The purpose
is both to make it simpler for users to export certain items, and in addition secure a better
consistency. Hence the end user is not burdened to provide details, and only a script with quite
a few lines will be needed.

Currently only volumes are exposed, but this will be extended in the near future.

.. _example-export-volumes-rms:

Exporting volumetrics from RMS
------------------------------

Volumetrics in RMS is always done in a so-called volume jobs. The intention with the simplification
is to use the RMS API behind the scene to retrieve all necessary data needed for ``fmu.dataio``.

Example:

.. code-block:: python

    from fmu.dataio.export.rms import export_volumetrics
    ...

    # here 'Geogrid' is the grid model name, and 'geogrid_volumes' is the name of the volume job
    outfiles = export_volumetrics(project, "Geogrid", "geogrid_volumes")

    print(f"Output volumes to {outfiles}")

Most ``dataio`` settings are here defaulted, but some keys can be altered optionally, e.g.:

.. code-block:: python

    outfiles = export_volumetrics(
        project,
        "Geogrid",
        "geogrid_volumes",
        global_variables="../whatever/global_variables.yml",
        tagname="vol",
        subfolder="volumes",
    )


Details
-------

.. automodule:: fmu.dataio.export.rms.volumetrics
    :members:
