Overview
========

``fmu-dataio`` is a library for exporting data out of FMU workflows. In addition to making
data export on the current (filename-based) standard easier, it also creates and attaches
metadata to the exported data.

In a Python script running somewhere in the FMU workflow, usage of ``fmu-dataio`` looks
roughly like this (more detailed working examples are provided elsewhere in this documentation):

.. code-block:: python

    from fmu.dataio import ExportData

    df = make_my_data() # how you create a data object is same as before
    cfg = get_global_config() # how you read global config is same as before

    exp = ExportData( # ExportData takes a number of arguments, these are examples.
        config=cfg,
        content="volumes",
    )
    exp.export(df) # this is the export.

Although long-term intention is to discontinue this, exported data will still be stored
to the underlying disk structure on which FMU is running (i.e. /scratch). When storing
data to disk, ``fmu-dataio`` will store the data file according to the current filename-oriented
FMU data standard. Next to it, with a corresponding file name, it will store the metadata according
to the metadata-based FMU data standard.

Example:

.. code-block:: console

    share/results/tables/mytable.csv
    share/results/tables/.mytable.csv.yml <-- metadata


Context on multiple levels are added to these metadata. First of all, references to
Equinor master data is required, but also FMU-specific context such as which model was
used to produce the data, which realization and iteration a specific file is produced in,
and much more.


Static and object-specific metadata
-----------------------------------

Metadata are in general "data about the data". For instance a pure surface
export file (e.g. irap binary) will have information about data itself (like
values in the map, and bounding box) but the file has no idea of which FMU run it
belongs to, or which field it comes from or what data contents it is representing.

Some metadata contents are *static for the model*, meaning that they will be
the same for all runs of a specific model setup. Some metadata contents are *static to 
the case*, meaning that they will be the same for all data belonging to a specific case.
Other metadata are object-specific, i.e. they will vary per item which is exported.

Given the amount of data produced by a single FMU run, it is impossible to contextualize
the data manually on this granularity. Therefore, ``fmu-dataio`` automates this.

The data model used for FMU results is a partly denormalized data model, meaning that some
static data will be repeated across many data objects. Example: Each exported data object contains
basic information about the FMU case it belongs to, such as a unique ID for this case,
its name, the user that made it, which model template was used, etc. This information
is stored in *every* exported .yml file. This may seem counter-intuitive and differs
from a relational database (where this information would typically be stored once, and
referred to when needed).

The FMU results data model is further documented `here <./datamodel.html>`__
