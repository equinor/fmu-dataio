Overview
========

``fmu-dataio`` is a library for exporting data out of FMU workflows. In addition to making
data export on the current (filename-based) standard easier, it also exports rich metadata
making it possible to utilize cloud storage (Sumo). Further, centralizing export methods
like this makes workflows simpler and less prone to break when changes are made.

The library works both inside RMS and outside RMS.

Static and object-specific metadata
-----------------------------------

Metadata are in general "data about the data". For instance a pure surface
export file (e.g. irap binary) will have information about data itself (like
values in the map, and bounding box) but the file have no idea of which FMU run it
belongs to, or which field it comes from or what horizon is represents.

Some metadata contents are *static for the model*, meaning that they will be
the same for all runs of a specific model setup. Examples are masterdata relations
(**field**, **country**, etc).

Some metadata contents are *static to the case*, meaning that they will be the same
for all data belonging to a specific case. Example: Metadata about the case itself.

Other metadata are object-specific, i.e. they will vary per item which is exported. For
instance, content metadata are object-specific as some surfaces are in depth domain, some in
time and other represents e.g. an average property.

Basicly it works like this in a FMU run:

    * *Metadata static for the model* comes from the fmu-config YAML file.
    * *Metadata static for the case* comes from ERT.
    * *Object-specific metadata* must be provided in the export.

The metadata is materialized as .yaml-files together with the actual data files, as
described in the FMU standard. This means that for each file, e.g. an exported surface
called `my_surface.gri` there will be a corresponding .yaml file called `.mysurface.gri.yml`.

The data model used for FMU results is a partly denormalized data model, meaning that some
static data will be repeated across many data objects. Example: Each exported data object contains
basic information about the FMU case it belongs to, such as a unique ID for this case,
its name, the user that made it, which model template was used, etc. This information
if stored in *every* exported .yml file. This may seem counter-intuitive and differs
from a relational database (where this information would typically be stored once, and
refered to when needed).

The FMU results data model is further documented `here <./datamodel.html>`__

Getting started
===============

To get started, your FMU workflow must be retrofitted with a few improvements further
described `here <./preparations.html>`__