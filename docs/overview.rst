Overview
========

The ``fmu-dataio`` library works as an engine to transfer data (results) from
an FMU run to files with metadata, ready for uploading in SUMO

The library works both inside RMS and outside RMS.

Static and dynamic metadata
-----------------------------------

Metadata are in general "additional data about the data". For instance a pure surface
export file (e.g. irap binary) will have information about data itself (like
values in the map, and bounding box) but the file have no idea of which FMU run it
belongs to, or which field it comes from.

For an export some of the metadata are *static*, which mean that it will note change for
a run. Typical static metadata are field, country and coordinate system information

Other metadata are dynamic, i.e. they will vary per item which is exported. For
instance, content metadata are dynamic as some surfaces are in depth domain, some in
time and other represents e.g. an average property.

Basicly it works like this in a FMU run:

    * Static metadata comes from the fmuconfig YAML file.
    * Dynamic metadata must be provided in the export

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


Prepare fmu-config
------------------

Text to comes
