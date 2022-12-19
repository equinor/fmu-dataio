Prepare FMU workflow to produce rich metadata
=============================================

In order to start using fmu-dataio and produce valid metadata for FMU output, some
preparations are necessary to your workflow. Expected time consumption is less than an hour.

You will do the following:
- Find and enter some key model metadata into ``global_variables.yml``
- Include an ERT workflow for establishing case metadata
- Include one script for data export

You may also find it helpful to look at the Drogon tutorial project for this. This is
in the category "really easy when you know how to do it" so don't hesitate to ask for help!

Insert key model metadata into global_variables.yml
---------------------------------------------------

In ``fmuconfig/input/``, create ``_masterdata.yml``. The content of this file shall be
references to master data. We get our master data from SMDA, so you need to do some
lookups there to find your masterdata references. In the FMU metadata, we currently use
4 master data entries: country, discovery, field, coordinate_system and stratigraphic_column.

.. note:: 
  Master data are "data about the business entities that provide context for business
  transactions" (Wikipedia). In other words: *Definitions* of things that we refer to
  across processes and entities. E.g. if two software, in two parts of the company, are
  referring to the same thing, we need to agree on definitions of that specific thing
  and we need to record those definitions in a way that makes us certain that we are, in
  fact, referring to the same thing. An example is the country of Norway. Simply saying
  "Norway" is not enough. We can also refer to Norway as "Norge", "Noreg", "Norga",
  "Vuodna" or "Nöörje". So, we define a universally unique identifier for the entity of
  Norway, and we refer to this instead. And all that various names are *properties* on
  this commonly defined entity. These definitions, we store as *master data* because no
  single applications shall own this definition.


This is the content of ``_masterdata.yml`` from the Drogon example. Adjust to your needs:

.. code-block:: yaml

    smda:
    country:
      - identifier: Norway
        uuid: ad214d85-8a1d-19da-e053-c918a4889309
    discovery:
      - short_identifier: DROGON
        uuid: ad214d85-8a1d-19da-e053-c918a4889309
    field:
      - identifier: DROGON
        uuid: 00000000-0000-0000-0000-000000000000
    coordinate_system:
      identifier: ST_WGS84_UTM37N_P32637
      uuid: ad214d85-dac7-19da-e053-c918a4889309
    stratigraphic_column:
      identifier: DROGON_HAS_NO_STRATCOLUMN
      uuid: 00000000-0000-0000-0000-000000000000

Note that ``country``, ``discovery`` and ``field`` are lists. Most of us will only need one
entry in the list, but in some cases, more will be required. E.g. if a model is covering
more than one field, or more than one country.

To find the unique identifiers, go to https://smda.equinor.com/ -> viewer. You can usually
use the ``identifier`` (often just the name) to identify the correct entity.

Next, establish ``_access.yml``. In this file, you will enter some information related
to how FMU results from your workflow are to be governed when it comes to access rights.


Example from Drogon:

.. code-block:: yaml

    asset:
      name: Drogon
    ssdl:
      access_level: internal
      rep_include: true


Under ``asset.name`` you will put the name of your asset. This is only relevant if you plan
to upload data to Sumo, and in that case, you will be told by the Sumo team what asset
should be.

.. note::
  "I cannot find asset in SMDA, and why does asset not have a unique ID"?

  Currently, "asset" is not covered by master data/SMDA. However, it is a vitally important
  piece of information that governs both ownership and access to data when stored in the
  cloud. Often, asset is identical to "field" but not always.

Under ``ssdl``, you will enter some defaults regarding data sharing with the Subsurface Data Lake.
In the Drogon example, data are by default available to SSDL, but you may want to do differently.

Note that you can override this default setting at any point when exporting data, and also
note that no data will be lifted to the lake without explicit action by the data owner.


Finally, establish ``_stratigraphy.yml``. This is a bit more heavy, and relates to the
``stratigraphic_column`` referred to earlier. In short, when applicable, stratigraphic intervals
used in the model setup must be mapped to their respective references in the stratigraphic column.
We do this, by listing the names used inside the model (usually the names reflected in RMS).

``_stratigraphy.yml`` contains a dictionary per stratigraphic entity in the model, with keys
reflecting different properties of that stratigraphic level.

The *key* of each entry is identical to the name used in RMS. There are two required
values: ``name`` (the official name as listed in the stratigraphic column) and 
``stratigraphic`` (True if stratigraphic level is listed in the stratigraphic columns, False if not).

In example below, observe that "TopVolantis" is a home-made name for ``VOLANTIS GP. Top`` 
and is in the stratigraphic column, while "Seabed" is not.

In addition, you may want to use some of the *optional* values:
- `alias` is a list of known aliases for this stratigraphic entity.
- `stratigraphic_alias` is a list of valid *stratigraphic* aliases for this entry, e.g. when a specific horizon is the top of both a formation and a group, or similar.

From the Drogon tutorial:

.. code-block:: yaml
  
    # HORIZONS
    Seabed:
        stratigraphic: False
        name: Seabed

    TopVolantis:
        stratigraphic: True
        name: VOLANTIS GP. Top
        alias:
        - TopVOLANTIS
        - TOP_VOLANTIS
        stratigraphic_alias:
        - TopValysar
        - Valysar Fm. Top

    TopTherys:
        stratigraphic: True
        name: Therys Fm. Top


    # ZONES/INTERVALS

    Above:
        stratigraphic: False
        name: Above

    Valysar:
        stratigraphic: True
        name: Valysar Fm.


Finally, in ``global_variables.yml`` we will do 2 things. First, we will enter a ``model``
block which contains some information about the model setup. Then, we will include the
3 files made above. Example from Drogon:

.. code-block:: yaml

    [...]

    (rest of global_variables.yml)

    #===================================================================================
    # Elements pertaining to metadata
    #===================================================================================

    model:
      name: ff
      revision: 22.1.0.dev

    masterdata: !include _masterdata.yml
    access: !include _access.yml
    stratigraphy: !include _stratigraphy.yml

You are done with the first part! This is to a large degree a one-off thing, and you
should not expect to have to do this again and again.


Workflow for creating case metadata
-----------------------------------

For each FMU case, a set of metadata is generated and temporarily stored on
/scratch/<case_directory>/share/metadata/fmu_results.yml. The case metadata are read by
individual export jobs, and, if you opt to upload data into Sumo, the case metadata are
used to register the case.

Case metadata are made by a hooked ERT workflow running ``PRE_SIMULATION``.

To make this, first create the workflow file in ``ert/bin/workflows/xhook_create_case_metadata``.

.. note::
    The "xhook" prefix is convention, but not mandatory. As all workflows will be included in the
    ERT GUI dropdown, the "hook" prefix signals that the workflow is not intended to be run manually. Further, 
    the "x" makes it go to the bottom of the (alphabetically) sorted dropdown. If you have many workflows,
    this makes things a little bit more tidy.

The workflow calls a pre-installed workflow job: ``WF_CREATE_CASE_METADATA``. Example script 
from the Drogon workflow:

.. code-block::

    -- Create case metadata
    --                       ert_caseroot                 ert_configpath    ert_casename   ert_username
    WF_CREATE_CASE_METADATA  <SCRATCH>/<USER>/<CASE_DIR>  <CONFIG_PATH>     <CASE_DIR>     <USER>

    -- This workflow is intended to be ran as a HOOK workflow.

    -- Arguments:
    -- ert_caseroot (Path): The absolute path to the root of the case on /scratch
    -- ert_configpath (Path): The absolute path to the ERT config
    -- ert_casename (str): The name of the case
    -- ert_user (str): The username used in ERT

    -- Optional arguments:
    --  --sumo: If passed, case will be registered on Sumo. Use this is intention to upload data.
    --  --sumo_env (str): Specify Sumo environment. Default: prod
    --  --global_variables_path (str): Path to global variables relative to CONFIG path
    --  --verbosity (str): Python logging level to use
    -- 
    -- NOTE! If using optional arguments, note that the "--" annotation will be interpreted
    --       as comments by ERT if not wrapped in quotes. This is the syntax to use:
    --       (existing arguments) "--sumo" "--sumo_env" dev "--verbosity" DEBUG

.. note::
    Note that there are references to Sumo in the script above. You don't have to worry
    about that for now, but we will return to this if applicable.


Now, load this workflow in your ERT config file and make it a HOOK workflow:

.. code-block::
  
    -- Hook workflow for creating case metadata and (optional) registering case on Sumo
    LOAD_WORKFLOW   ../../bin/workflows/xhook_create_case_metadata
    HOOK_WORKFLOW   xhook_create_case_metadata  PRE_SIMULATION


.. note::
    In the Drogon example, you will notice that the loading is done in the ``install_custom_jobs.ert``
    include file, while the HOOK_WORKFLOW call is in the main config file.

You can now start ERT to verify that the workflow is loading and working. You should see
the workflow appear in the workflows dropdown, and when you run a case, you should see
case metadata appear in ``scratch/<field>/<casedir>/share/metadata/fmu_results.yml``.


Include a data export job
-------------------------

To verify that data export now works, add one job to your workflow. Pick something simple,
such as depth surfaces from the structural model or similar. Use one of the examples on
the next page to get going, and/or have a look at the Drogon tutorial project.

**What about Sumo**
Odds are that you are implementing rich metadata export so that you can start utilizing
Sumo. Producing metadata with exported data is a pre-requisite for using Sumo. When you
have undertaken the steps above, you are good to go! Head to the 
`Sumo <https://fmu-sumo.app.radix.equinor.com/documentation>`__ documentation to
get going 👍
