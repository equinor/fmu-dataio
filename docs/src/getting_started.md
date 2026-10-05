# Getting Started

In order to start using fmu-dataio and produce rich metadata for FMU output,
some preparations are necessary to your workflow. Expected time consumption is
less than an hour.

You will do the following:

1. Initialize and open FMU Settings to set key model metadata, including Equinor master data
2. Include an ERT workflow for generating case metadata
3. Include (at least) one job for data export

You may also find it helpful to look at the Drogon tutorial project for this.
This is in the category "really easy when you know how to do it" so don't
hesitate to ask for help!

## 1. How to get started with FMU Settings

References to the Equinor master data are essential context for enabling other
systems to use FMU results. Previously, these master data and key model metadata
has been defined as part of the `global_master_config.yml` file. 
**FMU Settings** is a new solution developed to make this process 
easier, more robust, and less error-prone, by replacing these sections in the 
`global_master_config.yml` with a GUI.
See [FMU Settings documentation](https://equinor.github.io/fmu-settings/getting_started.html) 
for how to get started with FMU Settings.


```{note}
Master data are "data about the business entities that provide context for
business transactions" (Wikipedia). In other words: *Definitions* of things
that we refer to across processes and entities. E.g. if two software, in two
parts of the company, are referring to the same thing, we need to agree on
definitions of that specific thing and we need to record those definitions in
a way that makes us certain that we are, in fact, referring to the same thing.
An example is the country of Norway. Simply saying "Norway" is not enough. We
can also refer to Norway as "Norge", "Noreg", "Norga", "Vuodna" or "Nöörje".
So, we define a universally unique identifier for the entity of Norway, and we
refer to this instead. And all those various names are *properties* on this
commonly defined entity. These definitions, we store as *master data* because
no single applications shall own this definition.
```

When you have initialized and started using **FMU Settings** for your project, the following sections
should be removed from your `global_master_config.yml`, if they are present (this will mostly be 
relevant for the early onboarders), as these are replaced by FMU Settings:
- model
- masterdata
- access
- stratigraphy

Correspondingly, these files (in `/fmuconfig/input`) can be deleted, as they are not used anymore
- `_masterdata.yml` 
- `_access.yml` 
- `_stratigraphy.yml`

**Summary:** These sections should be ***removed*** from your `global_master_config.yml`, as all this is 
taken care of in FMU Settings:

```yaml
# [...]

# (rest of global_master_config.yml)

#===================================================================================
# Elements pertaining to metadata
#===================================================================================

model:
  name: ff
  revision: 22.1.0.dev

masterdata: !include _masterdata.yml
access: !include _access.yml
stratigraphy: !include _stratigraphy.yml
```


## 2. Workflow for creating case metadata

It is time to create the ERT workflow which will generate case metadata.
**Case metadata** are metadata about the specific *case* you are running. A
*case* in this context is a group of one or more ensembles, which will appear
in the same folder structure on /scratch.  Example:
`/scratch/<asset>/<user>/<CASE>/...`.

For each FMU case, a set of metadata is generated and stored on
`/scratch/<case_directory>/share/metadata/fmu_case.yml`. The case metadata are
read by individual export jobs, and, if you opt to upload data into Sumo, the
case metadata are used to register the case. Case metadata are made by a
hooked (pre-sim) Ert workflow running `PRE_SIMULATION`.

Add the pre-installed workflow job `WF_CREATE_CASE_METADATA` as a
[`HOOK_WORKFLOW_JOB`](https://fmu-docs.equinor.com/docs/ert/reference/configuration/keywords.html#hook-workflow-job)
in your ERT config file:

```sql
-- Hook workflow for creating case metadata and (optional) registering case on Sumo
HOOK_WORKFLOW_JOB  xhook_create_case_metadata  WF_CREATE_CASE_METADATA  "--sumo"  PRE_SIMULATION
```

````{note}
The `"--sumo"` argument is recommended and is used to register the case in
Sumo. If specified, `<SUMO_CASEPATH>` must be defined in the ERT config, for
example:

```sql
DEFINE <SUMO_CASEPATH> <SCRATCH>/<USER>/<CASE_DIR>
```
````

You can now start ERT to verify that the workflow is loading and working. You
should see the workflow appear in the workflows dropdown, and when you run a
case, you should see case metadata appear in
`scratch/<field>/<casedir>/share/metadata/fmu_case.yml`.


## 3. Include a data export job

To verify that data export now works, add one job to your RMS workflow. Pick
something simple, such as depth surfaces from the structural model or similar.
Use one of the examples on the next page to get going, and/or have a look at
the Drogon tutorial project.

## Continue the setup with Sumo

Your FMU workflow now has basic functionality in place for producing FMU results
with metadata. Return to the [Sumo documentation](https://fmu-docs.equinor.com/docs/sumo/guides) to continue.
