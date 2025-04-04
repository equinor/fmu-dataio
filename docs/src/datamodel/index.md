# The FMU results data model

This section describes the data model used for FMU results when exporting with
fmu-dataio. For the time being, the data model is hosted as part of fmu-dataio.

The data model described herein is new and shiny, and experimental in many aspects.
Any feedback on this is greatly appreciated. The most effective feedback is to apply
the data model, then use the resulting metadata.

The FMU data model is described using a [Pydantic](https://pydantic.dev/) model
which programmatically generates a [JSON Schema](https://json-schema.org/).

This schema contains rules and definitions for all attributes in the data model. This
means, in practice, that outgoing metadata from FMU needs to comply with the schema.
If data is uploaded to e.g. Sumo, validation will be done on the incoming data to ensure
consistency.


## Data model documentation

There are two closely related data models represented here: metadata generated from
an FMU realization and metadata generated on a case level. The structure and
documentation of these two models can be inspected from here.

```{eval-rst}
.. autosummary::
   :toctree: model/
   :recursive:


   .. toctree::
      :maxdepth: -1

      ~fmu.dataio._models.fmu_results.fmu_results.ObjectMetadata
      ~fmu.dataio._models.fmu_results.fmu_results.CaseMetadata
```


## About the data model

### Why is it made?

FMU is a mighty system developed by and for the subsurface community in Equinor, to
make reservoir modeling more efficient, less error-prone and more repeatable with higher quality,
mainly through automation of cross-disciplinary workflows. It combines off-the-shelf software
with in-house components such as the ERT orchestrator.

FMU is defined more and more by the data it produces, and direct and indirect dependencies on
output from FMU is increasing. When FMU results started to be regularly transferred to cloud
storage for direct consumption from 2017/2018 and outwards, the need for stable metadata on
outgoing data became immiment. Local development on Johan Sverdrup was initiated to cater
for the digital ecosystem evolving in and around that particular project, and the need for
generalizing became apparent with the development of Sumo, Webviz and other initiatives.

The purpose of the data model is to cater for the existing dependencies, as well as enable
more direct usage of FMU results in different contexts. The secondary objective of this
data model is to create a normalization layer between the components that create data
and the components that use those data. The data model is designed to also be adapted
to other sources of data than FMU.

### Scope of this data model

This data model covers data produced by FMU workflows. This includes data generated by
direct runs of model templates, data produced by pre-processing workflows, data produced
in individual realizations or hooked workflows, and data produced by post-processing workflows.

:::{note}
An example of a pre-processing workflow is a set of jobs modifying selected input data
for later use in the FMU workflows and/or for comparison with other results in a QC context.
:::

:::{note}
An example of a post-processing workflow is a script that aggregates results across many
realizations and/or iterations of an FMU case.
:::

This data model covers data that, in the FMU context, can be linked to a specific case.

Note that e.g. ERT and other components will, and should, have their own data models to
cater for their needs. It is not the intention of this data model to cover all aspects
of data in the FMU context. The scope is primarily data going *out* of FMU to be used elsewhere.


### A denormalized data model

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

:::{note}
The data model is only denormalized *to a certain point*. Most likely, it is better
described as a hybrid. Example: The concept of a *case* is used in FMU context. In the
outgoing metadata for FMU results, some information about the current case is included.
However, *details* about the case is out of scope. For this, a consumer would have to
refer to the owner of the *case* definition. In FMU contexts, this will be the workflow
manager (ERT).
:::


### Standardized vs anarchy

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


### Relations to other data models

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

- Be a translating layer between individual softwares' data models and the FMU results data model.
- Enable fully-automated materialization of metadata during FMU runs (hundreds of thousands of files being made)
- Abstract the FMU results data model through Python methods and functions, allowing them to be embedded into other systems - helping maintain a centralized definition of this data model.


### The parent/child principle

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

```{eval-rst}
.. note::

  **Dot-annotation** - we like it and use it. This is what it means:

  The metadata structure is a dictionary-like structure, e.g.

  .. code-block:: json

      {
          "myfirstkey": {
              "mykey": "myvalue",
              "anotherkey": "anothervalue"
          }
      }
```

Annotating tracks along a dictionary can be tricky. With dot-annotation, we can
refer to `mykey` in the example above as `myfirstkey.mykey`. This will be a
pointer to `myvalue` in this case. You will see dot annotation in the
explanations of the various metadata blocks below: Now you know what it means!

### Weaknesses

**uniqueness**

The data model currently has challenges wrt ensuring uniqueness. Uniqueness is a challenge
in this context, as a centralized data model cannot (and should not!) dictate in detail nor
define in detail which data an FMU user should be able to export from local workflows.

**understanding validation errors**

When validating against the current schema, understanding the reasons for non-validation
can be tricky. The root cause of this is the use of conditional logic in the schemas -
a functionality JSON Schema is not designed for. See Logical rules below.


### Logical rules

The schema contains some logical rules which are applied during validation. These are
rules of type "if this, then that". They are, however, not explicitly written (nor readable)
as such directly. This type of logic is implemented in the schema by explicitly generating
subschemas that A) are only valid for specific conditions, and B) contain requirements for
that specific situation. In this manner, one can assure that if a specific condition is
met, the associated requirements for that condition is used.

Example:

```json
"oneOf": [
  {
    "$comment": "Conditional schema A - 'if class == case make myproperty required'",
    "required": [
      "myproperty"
    ],
    "properties": {
      "class": {
        "enum": ["case"]
        },
      "myproperty": {
        "type": "string",
        "example": "sometext"
      }
    }
  },
  {
    "$comment": "Conditional schema B - 'if class != case do NOT make myproperty required'",
    "properties": {
      "myproperty": {
        "type": "string",
        "example": "sometext"
      }
    }
  }
]
```

For metadata describing a `case`, requirements are different compared to
metadata describing data objects.

For selected contents, a content-specific block under `data` is required. This
is implemented for `fluid_contact`, `field_outline` and `seismic`.


## Validation of data

When fmu-dataio exports data from FMU workflows, it produces a pair of data + metadata. The two are
considered one entity. Data consumers who wish to validate the correct match of data and metadata can
do so by verifying recreation of `file.checksum_md5` on the data object only. Metadata is not considered
when generating the checksum.

This checksum is the string representation of the hash created using RSA's `MD5` algorithm. This hash
was created from the _file_ that fmu-dataio exported. In most cases, this is the same file that are
provided to consumer. However, there are some exceptions:

- Seismic data may be transformed to other formats when stored out of FMU context and the checksum may
be invalid.


## Changes and revisions

The only constant is change, as we know, and in the case of the FMU results data model - definitely so.
The learning component here is huge, and there will be iterations. This poses a challenge, given that
there are existing dependencies on top of this data model already, and more are arriving.

To handle this, two important concepts has been introduced.

1. **Versioning**. The current version of the FMU metadata is
   **{{ FmuResultsSchema.VERSION }}**.

2. **Contractual attributes**. Within the FMU ecosystem, we need to retain the
   ability to do rapid changes to the data model. As we are in early days,
   unknowns will become knowns and unknown unknowns will become known unknowns.
   However, from the outside perspective some stability is required. Therefore,
   we have labelled some key attributes as *contractual*. They are listed at the
   top of the schema. This is not to say that they will never change - but they
   should not change erratically, and when we need to change them, this needs to
   be subject to alignment.

### Schema version changelog

{{ FmuResultsSchema.VERSION_CHANGELOG }}

### Contractual attributes

The following attributes are contractual:

{{ FmuResultsSchema.contractual }}

## Metadata example

Expand below to see a full example of valid metadata for surface exported from FMU.

```{eval-rst}
.. toggle::

   .. literalinclude:: ../../../examples/0.8.0/surface_depth.yml
      :language: yaml

```

You will find more examples in [fmu-dataio github repository](https://github.com/equinor/fmu-dataio/tree/main/examples/0.8.0).


## FAQ

We won't claim that these questions are really very *frequently* asked, but these are some
key questions you may have along the way.

**My existing FMU workflow does not produce any metadata. Now I am told that it has to. What do I do?**

First step: Start using fmu-dataio in your workflow. You will get a lot for free using it, amongst
other things, metadata will start to appear from your workflow. To get started with fmu-dataio,
see [the overview section](../overview).

**This data model is not what I would have chosen. How can I change it?**

The FMU community (almost always) builds what the FMU community wants. The first step
would be to define what you are unhappy with, preferably formulated as an issue in the
[fmu-dataio github repository](https://github.com/equinor/fmu-dataio).

**This data model allows me to create a smashing data visualisation component, but I fear that it
is so immature that it will not be stable - will it change all the time?**

Yes, and no. It is definitely experimental and these are early days. Therefore, changes
will occur as learning is happening. Part of that learning comes from development of
components utilizing the data model, so your feedback may contribute to evolving this
data model. However, you should not expact erratic changes. The concept of Contractual attributes
are introduced for this exact purpose. We have also chosen to version the metadata - partly to
clearly separate from previous versions, but also for allowing smooth evolution going forward.
We don't yet know *exactly* how this will be done in practice, but perhaps you will tell us!
