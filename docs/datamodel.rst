The FMU results data model
##########################

This section describes the data model used for FMU results when exporting with
fmu-dataio. For the time being, the data model is hosted as part of fmu-datio.

  The data model described herein is new and shiny, and experimental in many aspects.
  Any feedback on this is greatly appreciated. The most effective feedback is to apply
  the data model, then use the resulting metadata.


The FMU data model is described using a `JSON Schema <https://json-schema.org/>`__ which
contains rules and definitions for all attributes in the data model. This means, in
practice, that outgoing metadata from FMU needs to comply with the schema. If data is
uploaded to e.g. Sumo, validation will be done on the incoming data to ensure consistency.

The full schema:

.. toggle::

   .. literalinclude:: ../schema/definitions/0.8.0/schema/fmu_results.json
      :language: js

|

For the average user, there is no need to deep-dive into the schema itself. The purpose
of fmu-dataio is to broker between the different other data models used in FMU, and the
definitions of FMU results. E.g. RMS has its data model, Eclipse has its data model, ERT
has its data model, and so on.

What you need to know is that for every data object exported out of FMU with the intention
of using in other contexts a metadata instance pertaining to this definition will also be
created.

About the data model
====================

Why is it made?
---------------

FMU is a mighty system developed by and for the subsurface community in Equinor, to
make reservoir modeling more efficient, less error-prone and more repeatable with higher quality,
mainly through automation of cross-disciplinary workflows.

FMU is defined more and more by the data it produces, and direct and indirect dependencies on
output from FMU is increasing. When FMU results started to be regularly transferred to cloud
storage for direct consumption from 2017/2018 and outwards, the need for stable metadata on
outgoing data became immiment. Local development on Johan Sverdrup was initiated to cater
for the digital ecosystem evolving in and around that particular project, and the need for
generalizing became apparent with the development of Sumo, Webviz and other initiatives.

The purpose of the data model is to cater for the existing dependencies, as well as enable
more direct usage of FMU results in different contexts.

A denormalized data model
-------------------------

The data model used for FMU results is a denormalized data model, at least to a certain
point. This means that the static data will be repeated many times. Example: Each exported data object contains
basic information about the FMU case it belongs to, such as a unique ID for this case,
its name, the user that made it, which model template was used, etc. This information
if stored in *every* exported .yml file. This may seem counterintuitive, and differs
from a relational database (where this information would typically be stored once, and
referred to when needed).

There are a few reasons for choosing a denormalized data model:

First, the components for creating a relational database containing these data is not and would
be extremely difficult to implement fast. Also, the nature of data in an FMU context is very distributed,
with lots of files spread across many files and folders (currently).

Second, a denormalized data model enables us to utilize search engine technologies for
for indexing. This is not efficient for a normalized data model. The penalty for 
duplicating metadata across many individual files is returned in speed and ease-of-use.

Note: The data model is only denormalized *to a certain point*. Most likely, it is better
described as a hybrid. Example: The concept of a *case* is used in FMU context. In the 
outgoing metadata for FMU results, some information about the current case is included.
However, *details* about the case is out of scope. For this, a consumer would have to
refer to the owner of the *case* definition. In FMU contexts, this will be the workflow
manager (ERT).


Standardized vs anarchy
----------------------

Creating a data model for FMU results brings with it some standard. In essence, this
represents the next evolution of the existing FMU standard. We haven't called it "FMU standard 2.0"
because although this would ressonate with many people, many would find it revolting. But,
sure, if you are so inclined you are allowed to think of it this way. The FMU standard 1.0
is centric around folder structure and file names - a pre-requisite for standardizing for
the good old days when files where files, folders were folders, and data could be consumed
by double-clicking. Or, by traversing the mounted file system.

With the transition to a cloud-native state comes numerous opportunities - but also great
responsibilities. Some of them are visible in the data model, and the data model is in itself
a testament to the most important of them: We need to get our data straight.

There are many challenges. Aligning with everyone and everything is one. We probably don't
succeed with that in the first iteration(s). Materializing metadata effectively, and without
hassle, during FMU runs (meaning that *everything* must be *fully automated* is another. This
is what fmu-dataio solves. But, finding the balance between *retaining flexibility* and 
*enforcing a standard* is perhaps the most tricky of all.

This data model has been designed with the great flexibility of FMU in mind. If you are
a geologist on an asset using FMU for something important, you need to be able to export
any data from *your* workflow and *use that data* without having to wait for someone else
to rebuild something. For FMU, one glove certainly does not fit all, and this has been
taken into account. While the data model and the associated validation will set some requirements
that you need to follow, you are still free to do more or less what you want.

We do, however, STRONGLY ENCOURAGE you to not invent too many private wheels. The risk
is that your data cannot be used by others.

The materialized metadata has a nested structure which can be represented by Python
dictionaries, yaml or json formats. The root level only contains key attributes, where
most are nested sub-dictionaries.


Relations to other data models
------------------------------

The data model for FMU results is designed with generalization in mind. While in practice
this data model cover data produced by, or in direct relations to, an FMU workflow - in 
*theory* it relates more to *subsurface predictive modeling* generally, than FMU specifically.

In Equinor, FMU is the primary system for creating, maintaining and using 3D predictive
numerical models for the subsurface. Therefore, FMU is the main use case for this data model.

There are plenty of other data models in play in the complex world of subsurface predictive modeling.
Each software applies its own data model, and in FMU this encompasses multiple different systems.

Similarly, there are other data models in the larger scope where FMU workflows represent
one out of many providors/consumers of data. A significant motivation for defining this
data model is to ensure consistency towards other systems and enable stable conditions for integration.

fmu-dataio has three important roles in this context:

* Be a translating layer between individual softwares' data models and the FMU results data model.
* Enable fully-automated materialization of metadata during FMU runs (hundreds of thousands of files being made)
* Abstract the FMU results data model through Python methods and functions, allowing them to be embedded into other systems - helping maintain a centralized definition of this data model.


The parent/child principle
--------------------------

In the FMU results data model, the traditional hierarchy of an FMU setup is not continued.
An individual file produced by an FMU workflow and exported to disk can be seen in
relations to a hiearchy looking something like this: case > iteration > realization > file

Many reading this will instinctively  disagree with this definition, and significant confusion
arises from trying to have meaningful discussions around this. There is no
unified definition of this hierarchy (despite many *claiming to have* such a definition).

In the FMU results data model, this hiearchy is flattened down to two levels: 
The Parent (*case*) and children to that parent (*files*). From this, it follows that the
most fundamental definition in this context is a *case*. To a large degree, this definition
belongs to the ERT workflow manager in the FMU context. For now, however, the case definitions
are extracted by-proxy from the file structure and from arguments passed to fmu-dataio.

Significant confusion can *also* arise from discussing the definition of a case, and the
validity of this hiearchy, of course. But consensus (albeit probably local minima) is that
this serves the needs.

Each file produced *in relations to* an FMU case (meaning *before*, *during* or *after*) is tagged
with information about the case - signalling that *this entity* belongs to *this case*. It is not
the intention of the FMU results data model to maintain *all* information about a case, and 
in the future it is expected that ERT will serve case information beyond the basics.


Uniqueness
----------

A key requirement to the data model is that it needs to facilitate granularity down to
absolute uniquness for each data object existing within an FMU case. Currently, this is
not trivial in practice. (See also ``fmu.workflow`` and ``file.relative_path``)


Assembling metadata
-------------------

Outgoing metadata for an individual data object (file) in the FMU context will contain
the relevant root attributes and blocks described further down this document. Not all
data objects will contain all attributes and blocks - this depends on the data type, the
context it is exported in and the data available.

Examples:

Data produced by pre- or post-processes will contain information about the ``case`` but 
not about ``realization`` implicitly meaning that they belong to a specific
case but not any specific realizations.

    The ``case`` object is a bit special: It represents the parent object, and records
    information about the case only. It follows the same patterns as for individual data objects
    but will not contain the ``data`` block which is mandatory for data objects.


Logical rules
-------------

The schema contains some logical rules which are applied during validation. These are
rules of type "if this, then that". Example: If **data.content** is "field_outline",
then **data.field_outline** shall be present.


The metadata structure
===============

    **Dot-annotation** - we like it and use it. This is what it means:

    The metadata structure is a dictionary-like structure, e.g.

    .. code-block:: json

        {
            "myfirstkey": {
                "mykey": "myvalue",
                "anotherkey": "anothervalue",
                }
        }
    
    ::

    Annotating tracks along a dictionary can be tricky. Wit dot-annotation, we can refer
    to ```mykey``` in the example above as ``myfirstkey.mykey``. This will be a pointer to
    ``myvalue`` in this case. You will see dot annotation in the explanations of the various metadata blocks below:
    Now you know what it means!

Root attributes
---------------

At the root level of the metadata, a few single-value attributes are used. These are
attributes saying something fundamental about these data:


* **$schema**: A reference to the schema which this metadata should be valid against.
* **version**: The version of the FMU results data model being used.
* **source**: The source of these data. Will always say "fmu" for FMU results.
* **class**: The fundamental type of data. Valid classes:
  * case
  * surface
  * table
  * cpgrid
  * cpgrid_property
  * polygons
  * cube
  * well
  * points


Blocks
-----------

The bulk of the metadata is gathered in specific blocks. *Blocks* are sub-dictionaries
containing a specific part of the metadata. Not all blocks are present in all materialized metadata,
and not all block sub-attributes are applied in all contexts. 


fmu
~~~

The ``fmu`` block contains all attributes specific to FMU. The idea is that the FMU results
data model can be applied to data from *other* sources - in which the fmu-specific stuff
may not make sense or be applicable. Within the fmu-block, there are more blocks:


**fmu.model**: The ``fmu.model`` block contains information about the model used. 

    Synonyms for "model" in this context are "template", "setup", etc. The term "model"
    is ultra-generic but was chosen before e.g. "template" as the latter deviates from
    daily communications and is, if possible, even more generic than "model".

**fmu.workflow**: The ``fmu.workflow`` block refers to specific subworkflows within the large
FMU workflow being ran. This has not (yet?) been standardized, mainly due to the lack
of programmatic access to the workflows being run in important software within FMU. 
One sub-attribute has been defined and is used:
**fmu.workflow.reference**: A string referring to which workflow this data object was exported by.

*A key usage of* ``fmu.workflow.reference`` *is related to ensuring uniqueness of data objects.*

    **Example of uniqueness challenge**
    During an hypothetical FMU workflow, a surface representing a specific horizon in
    depth is exported multiple times during the run for QC purposes. E.g. a representation
    of *Volantis Gp. Top* is first exported at the start of the workflow, then 2-3 times during
    depth conversion to record changes, then at the start of structural modeling, then 4-5
    times during structural modeling to record changes, then extracted from multiple grids.

    The end result is 10+ versions of *Volantis Gp. Top* which are identical except from
    which workflow they were produced.

**fmu.case**: The ``fmu.case`` block contains information about the case from which this data
object was exported. ``fmu.case`` has the following subattributes, and more may arrive:

* **fmu.case.name**: [string] The name of the case
* **fmu.case.uuid**: [uuid] The unique identifier of this case. Currently made by fmu.dataio. Future made by ERT?

* **fmu.case.user**: A block holding information about the user.

  * **fmu.case.user.id**: [string] A user identity reference.

* **fmu.case.description**: [list of strings] (a free-text description of this case) (optional)
* **fmu.case.restart_from**: [uuid] (experimental) The intention with this attribute is to flag when a case is a restart fromm another case. Implementation of this attribute in fmu-dataio is pending alignment with ERT.

    If an FMU data object is exported outside the case context, this block will not be present.

**fmu.iteration**: The ``fmu.iteration`` block contains information about the iteration this data object belongs to. The ``fmu.iteration`
has the following defined sub-attributes:

* **fmu.iteration.id**: [int] The internal ID of the iteration, typically represented by an integer.
* **fmu.iteration.uuid**: [uuid] The universally unique identifier for this iteration. It is a hash of ``fmu.case.uuid`` and ``fmu.iteration.id``.
* **fmu.iteration.name**: [string] The name of the iteration. This is typically reflecting the folder name on scratch. In ERT, custom names for iterations are supported, e.g. "pred". For this reason, if logic is implied, the name can be risky to trust - even if it often contains the ID, e.g. "iter-0"

**fmu.realization**: The ``fmu.realization`` block contains information about the realization this data object belongs to, with the following sub-attributes:

* **fmu.realization.id**: The internal ID of the realization, typically represented by an integer.
* **fmu.realization.uuid**: The universally unique identifier for this realization. It is a hash of ``fmu.case.uuid`` and ``fmu.iteration.uuid`` and ``fmu.realization.id``.
* **fmu.realization.name**: The name of the realization. This is typically reflecting the folder name on scratch. Custom names for realizations are not supported by ERT, but we still recommend to use ``fmu.realization.id`` for all usage except purely visual appearance.
* **fmu.realization.parameters**: These are the parameters used in this realization. It is a direct pass of ``parameters.txt`` and will contain key:value pairs representing the design parameters.

**fmu.jobs**: Directly pass "jobs.json". Temporarily deactivated in fmu-dataio pending further alignment with ERT.

    The blocks within the ``fmu`` section signal by their presence which context a data object is exported under. Example: If an
    aggregated object contains ``fmu.case`` and ``fmu.iteration`, but not ``fmu.realization``, it can be assumed that this object belongs
    to this ``case`` and ``iteration`` but not to any specific ``realization``.


file
~~~~

The ``file`` block contains references to this data object as a file on a disk. A filename in this context can be actual, or abstract. Particularly the ``relative_path`` is, and will most likely remain, an important identifier for individual file objects within an FMU case - irrespective of the existance of an actual file system.

* **file.relative_path**: [path] The path of a file relative to the case root.
* **file.absolute_path**: [path] The absolute path of a file, e.g. /scratch/field/user/case/etc
* **file.checksum_md5**: [string] A valid MD5 checksum of the file.

data
~~~~

The ``data`` block contains information about the data contains in this object.

* **data.content**: [string] The content of these data. Examples are "depth", "porosity", etc.

* **data.name**: [string] This is the identifying name of this data object. For surfaces, this is typically the horizon name or similar. Shall be compliant with the stratigraphic column if applicable.
* **data.stratigraphic**: [bool] True if this is defined in the stratigraphic column.
* **data.offset**: If a specific horizon is represented with an offset, e.g. "2 m below Top Volantis".

    If data object represents an interval, the data.top and data.base attributes can be used.

* **data.top**:
  
  * **data.top.name**: *As data.name*
  * **data.top.stratigraphic**: *As data.stratigraphic*
  * **data.top.offset**: *As data.offset*

* **data.base**:
  
  * **data.base.name**: *As data.name*
  * **data.base.stratigraphic**: *As data.stratigraphic*
  * **data.base.offset**: *As data.offset*

* **data.stratigraphic_alias**: [list] A list of strings representing stratigraphic aliases for this *data.name*. E.g. the top of the uppermost member of a formation will be alias to the top of the formation.
* **data.alias**: [list] Other known-as names for *data.name*. Typically names used within specific software, e.g. RMS and others.

* **data.properties**: A list of dictionary objects, where each object describes a property contained by this data object.
  
  * **data.properties.<item>.name**: [string] The name of this property.
  * **data.properties.<item>.attribute**: [string] The attribute.
  * **data.properties.<item>.is_discrete**: [bool] Flag if this property is is_discrete.
  * **data.properties.<item>.calculation**: [string] A reference to a calculation performed to derive this property.

    The ``data.properties`` concept is experimental. Use cases include surfaces containing multiple properties/attributes, grids with parameters, etc.

* **data.format**: [string] A reference to a known file format.
* **data.layout**: [string] A reference to the layout of the data object. Examples: "regular", "cornerpoint", "structured"
* **data.unit**: [string] A reference to a known unit. Examples. "m"
* **data.vertical_domain**: [string] A reference to a known vertical domain. Examples: "depth", "time"
* **data.depth_reference**: [string] A reference to a known depth reference. Examples: "msl", "seabed"

* **data.grid_model**: A block containing information pertaining to grid model content.
  
  * **data.grid_model.name**: [string] A name reference to this data.

* **data.spec**: A block containing the specs for this object, if applicable.
  
  * **data.spec.ncol**: [int] Number of columns
  * **data.spec.nrow**: [int] Number of rows
  * **data.spec.nlay**: [int] Number of layers
  * **data.spec.xori**: [float] Origin X coordinate
  * **data.spec.yori**: [float] Origin Y coordinate
  * **data.spec.xinc**: [float] X increment
  * **data.spec.yinc**: [float] Y increment
  * **data.spec.yflip**: [int] Y flip flag (from IRAP Binary)
  * **data.spec.rotation**: [float] Rotation (degrees)
  * **data.spec.undef**: [float] Number representing the Null value
  
* **data.bbox**: A block containing the bounding box for this data, if applicable
  
  * **data.bbox.xmin**: [float] Minimum X coordinate
  * **data.bbox.xmax**: [float] Maximum X coordinate
  * **data.bbox.ymin**: [float] Minimum Y coordinate
  * **data.bbox.ymax**: [float] Maximum Y coordinate
  * **data.bbox.zmin**: [float] Minimum Z coordinate
  * **data.bbox.zmax**: [float] Maximum Z coordinate


* **data.time**: A block containing lists of objects describing timestamp information for this data object, if applicable.

  * **data.time.value**: [datetime] A datetime representation
  * **data.time.label**: [string] A label corresponding to the timestamp

    data.time items can be repeated to include many time stamps

* **data.is_prediction**: [bool] True if this is a prediction
* **data.is_observation**: [bool] True if this is an observation
* **data.description**: [list] A list of strings, freetext description of this data, if applicable.

Conditional attributes of the data block:

* **data.fluid_contact**: A block describing a fluid contact. Shall be present if "data.content" == "fluid_contact"
  
  * **data.fluid_contact.contact**: [string] A known type of contact. Examples: "owc", "fwl"
  * **data.fluid_contact.truncated**: [bool] If True, this is a representation of a contact surface which is truncated to stratigraphy.

* **data.field_outline**: A block describing a field outline. Shall be present if "data.content" == "field_outline"
  
  * **data.field_outline.contact**: The fluid contact used to define the field outline.

* **data.seismic**: A block describing seismic data. Shall be present if "data.content" == "seismic"
  
  * **data.seismic.attribute**: [string] A known seismic attribute.
  * **data.seismic.zrange**: [float] The z-range applied.
  * **data.seismic.filter_size**: [float] The filter size applied.
  * **data.seismic.scaling_factor**: [float] The scaling factor applied.


display
~~~~~~~

The ``display`` block contains information related to how this data object should/could be displayed.
As a general rule, the consumer of data is responsible for figuring out how a specific data object shall
be displayed. However, we use this block to communicate preferences from the data producers perspective.

We also maintain this block due to legacy reasons. No logic should be placed on the ``display`` block.

* **display.name**: A display-friendly version of ``data.name``.
* **display.subtitle**: A display-friendly subtitle.

* **display.line**: (Experimental) A block containing display information for line objects.

  * **display.line.show**: [bool] Show a line
  * **display.line.color**: [string] A reference to a known color.

* **display.points**: (Experimental) A block containing display information for point(s) objects.

  * **display.points.show**: [bool] Show points.
  * **display.points.color**: [string] A reference to a known color.

* **display.contours**: (Experimental) A block containing display information for contours.

  * **display.contours.show**: [bool] Show contours.
  * **display.contours.color**: [string] A reference to a known color.

* **display.fill**: (Experimental) A block containing display information for fill.

  * **display.fill.show**: [bool] Show fill.
  * **display.fill.color**: [string] A reference to a known color.
  * **display.fill.colormap**: [string] A reference to a known color map.
  * **display.fill.display_min**: [float] The value to use as minimum value when displaying.
  * **display.fill.display_max**: [float] The value to use as maximum value when displaying.



access
~~~~~~

The ``access`` block contains information related to acces control for this data object.

* **asset**: A block containing information about the owner asset of these data.

  * **access.asset.name**: [string] A string referring to a known asset name.

* **access.ssdl**: A block containing information related to SSDL. Note that this is kept due to legacy.
  
  * **access.ssdl.access_level**: [string] The SSDL access level (internal/asset)
  * **access.ssdl.rep_include**: [bool] Flag if this data is to be shown in REP or not.

    We fully acknowledge that horrible pattern of putting application-specific information into a data model like this. However
    for legacy reasons this is kept until better options exists.


masterdata
~~~~~~~~~~

The ``masterdata`` block contains information related to masterdata. Currently, smda holds the masterdata.

* **masterdata.smda**: Block containing SMDA-related attributes.

  * **masterdata.smda.country**: [list] A list of strings referring to countries known to SMDA. First item is primary.
  * **masterdata.smda.discovery**: [list] A list of strings referring to discoveries known to SMDA. First item is primary.
  * **masterdata.smda.field**: [list] A list of strings referring to fields known to SMDA. First item is primary.

* **masterdata.smda.coordinate_system**: Reference to coordinate system known to SMDA
 
  * **masterdata.smda.coordinate_system.identifier**: [string] Identifier known to SMDA
  * **masterdata.smda.coordinate_system.uuid**: [uuid] A UUID known to SMDA

* **masterdata.smda.stratigraphic_column**: Reference to stratigraphic column known to SMDA

  * **masterdata.smda.stratigraphic_column.identifier**: [string] Identifier known to SMDA
  * **masterdata.smda.stratigraphic_column.uuid**: [uuid] A UUID known to SMDA


tracklog
~~~~~~~~

The tracklog block contains a record of events recorded on these data. This is experimental for now.
The tracklog is a list of *tracklog_events* with the following definition:

* **tracklog.<tracklog_event>**: An event.
  * **tracklog.<tracklog_event>.datetime**: [datetime] Timestamp of the event
  * **tracklog.<tracklog_event>.user**: [string] Identification of user associated with the event
  * **tracklog.<tracklog_event>.event**: [string] String representing the event


    The "tracklog" concept is included but considered heavily experimental for now. The concept of
    data lineage goes far beyond this, and this should not be read as the full lineage of these data.



Changes and revisions
---------------------

The only constant is change, as we know, and in the case of the FMU results data model - definitely so.
The learning component here is huge, and there will be iterations. This poses a challenge, given that
there are existing dependencies on top of this data model already, and more are arriving.

To handle this, two important concepts has been introduced.

1) **Versioning**. The current version of the FMU metadata is 0.8.0. This version is likely to remain for a while. (We have not yet figured out how to best deal with versioning. Have good ideas? Bring them!)
2) **Contractual attributes**. Within the FMU ecosystem, we need to retain the ability to do rapid changes to the data model. As we are in early days, unknowns will become knowns and unknown unknowns will become known unknowns. However, from the outside perspective some stability is required. Therefore, we have labelled some key attributes as *contractual*. They are listed at the top of the schema. This is not to say that they will never change - but they should not change erratically, and when we need to change them, this needs to be subject to alignment.


Contractual attributes
----------------------

The following attributes are contractual:

* class
* source
* version
* tracklog
* data.format
* data.name
* data.stratigraphic
* data.alias
* data.stratigraphic_alias
* data.offset
* data.content
* data.vertical_domain
* data.grid_model
* data.bbox
* data.is_prediction
* data.is_observation
* data.seismic.attribute
* access
* masterdata
* fmu.model
* fmu.workflow
* fmu.case
* fmu.iteration
* fmu.realization.name
* fmu.realization.id
* fmu.realization.uuid
* fmu.aggregation.operation
* fmu.aggregation.realization_ids
* file


Required vs non-required
------------------------

Not all attributes are required in all contexts. For details, please refer to the
actual schema.


Metadata example
----------------

Expand below to see a full example of valid metadata for surface exported from FMU.

.. toggle::

   .. literalinclude:: ../schema/definitions/0.8.0/examples/surface_depth.yml
      :language: yaml

|


FAQ
===

We won't claim that these questions are really very *frequently* asked, but these are some
key questions you may have along the way.

**My existing FMU workflow does not produce any metadata. Now I am told that it has to. What do I do?**
First step: Start using fmu-dataio in your workflow. You will get a lot for free using it, amongst
other things, metadata will start to appear from your workflow. To get started with fmu-dataio,
see [SOME OTHER SECTION] of this documentation.

**This data model is not what I would have chosen. How can I change it?**
The FMU community (almost always) builds what the FMU community wants. The first step
would be to define what you are unhappy with, preferably formulated as an issue in the
`fmu-dataio github repository <https://github.com/equinor/fmu-dataio>`__. 
(If your comments are Equinor internal, please reach out to either Per Olav (peesv) or Jan (jriv).)

**This data model allows me to create a smashing data visualisation component, but I fear that it
is so immature that it will not be stable - will it change all the time?**
Yes, and no. It is definitely experimental and these are early days. Therefore, changes
will occur as learning is happening. Part of that learning comes from development of
components utilizing the data model, so your feedback may contribute to evolving this
data model. However, you should not expact erratic changes. The concept of Contractual attributes
are introduced for this exact purpose. We have also chosen to version the metadata - partly to
clearly separate from previous versions, but also for allowing smooth evolution going forward.
We don't yet know *exactly* how this will be done in practice, but perhaps you will tell us!