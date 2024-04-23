Getting started
===============

In order to start using fmu-dataio and produce rich metadata for FMU output, some
preparations are necessary to your workflow. Expected time consumption is less than an hour.

You will do the following:

    * Find and enter some key model metadata into ``global_variables.yml``, including references to Equinor masterdata.
    * Include an ERT workflow for generating case metadata
    * Include one script for data export

You may also find it helpful to look at the Drogon tutorial project for this. This is
in the category "really easy when you know how to do it" so don't hesitate to ask for help!

global_variables.yml | **masterdata**
-------------------------------------

References to the Equinor masterdata are essential context for enabling other systems to
use FMU results.

In ``fmuconfig/input/``, create ``_masterdata.yml``. The content of this file shall be
references to Equinor master data. We get our master data from SMDA, so you need to do some
lookups there to find your references.

.. note:: 
  Master data are "data about the business entities that provide context for business
  transactions" (Wikipedia). In other words: *Definitions* of things that we refer to
  across processes and entities. E.g. if two software, in two parts of the company, are
  referring to the same thing, we need to agree on definitions of that specific thing
  and we need to record those definitions in a way that makes us certain that we are, in
  fact, referring to the same thing. An example is the country of Norway. Simply saying
  "Norway" is not enough. We can also refer to Norway as "Norge", "Noreg", "Norga",
  "Vuodna" or "Nöörje". So, we define a universally unique identifier for the entity of
  Norway, and we refer to this instead. And all those various names are *properties* on
  this commonly defined entity. These definitions, we store as *master data* because no
  single applications shall own this definition.


This is an example of ``_masterdata.yml`` from Drogon. Adjust to your needs:

.. code-block:: yaml

    # Note! Drogon is synthetic, so UUID's below are examples.

    smda:
      country:
        - identifier: Westeros
          uuid: 00000000-0000-0000-0000-000000000000
      discovery:
        - short_identifier: DROGON
          uuid: 00000000-0000-0000-0000-000000000000
      field:
        - identifier: DROGON
          uuid: 00000000-0000-0000-0000-000000000000
      coordinate_system:
        identifier: ST_WGS84_UTM37N_P12345
        uuid: 00000000-0000-0000-0000-000000000000
      stratigraphic_column:
        identifier: DROGON_2008
        uuid: 00000000-0000-0000-0000-000000000000

Note that ``country``, ``discovery`` and ``field`` are lists (can have more than one),
while ``coordinate_system`` and ``stratigraphic_column`` are not.

To find the information for your model, use `SMDA Viewer <https://opus.smda.equinor.com/smda_viewer/>`_. 
You will see a number of topics, and below each topic you will see several tiles.
(Direct links to the tiles you need will be provided further down, but clicking around a
bit in SMDA is encouraged to get a feel for what our master data looks like.)

Navigate to the `Fields <https://opus.smda.equinor.com/smda_viewer/fields>`_ section. Use
the filters to focus the list of fields, until you are able to find yours. In the list
of fields, highlight the line corresponding to your field (or fields if your model covers
more than one field).

Click the FMU-logo in the top right menu to open the FMU Metadata generation dialogue.

Review the settings and make necessary changes. You can remove erroneous data, empty
discoveries, etc. Choose the appropriate Stratigraphic Column and 
Coordinate Reference System (use same as in RMS) from the drop-down menus.

.. note::
  To find the coordinate system used in RMS: In RMS, select ``tools`` > ``Coordinate system``.

Copy the generated YAML content into your `_masterdata.yml`


global_variables.yml | **access**
---------------------------------

Next, create ``_access.yml``. In this file, you will enter some information related
to how FMU results from your workflow are to be governed when it comes to access rights.


Example from Drogon:

.. code-block:: yaml

    asset:
      name: Drogon
    ssdl:
      access_level: internal
      rep_include: true


Under ``asset.name`` you will put the name of your asset. If you plan to upload data to
Sumo, you will be told by the Sumo team what asset should be.

.. note::
  Currently, the "asset" concept is not covered by our masterdata. However, it is an important
  piece of information that governs both ownership and access to data when stored in the
  cloud. Sometimes, asset is identical to "field" but frequently it is not.

Under ``ssdl``, you will enter some defaults regarding data sharing with the Subsurface Data Lake.

The ``ssdl.access_level`` sets the (default) sensitivity of exported data. Valid entries
here are ``internal`` and ``restricted``. The ``ssdl.rep_include`` sets the default flag
for signalling inclusion of exported data in the Reservoir Experience Platform. This is
a boolean, and valid entries are ``True`` and ``False``.

.. note::
  The ``access.ssdl.access_level`` is currently also used for access handling in Sumo.

Note that these are defaults. You can override these settings at any point when exporting
data, and also note that no data will be lifted to the datalake without explicit action by you.


global_variables.yml | **stratigraphy**
---------------------------------------

Finally, establish ``_stratigraphy.yml``. This is a bit more heavy, and relates to the
``stratigraphic_column`` referred to earlier. In short, when applicable, stratigraphic intervals
used in the model setup must be mapped to their respective references in the stratigraphic column.
The stratigraphic elements do not (currently) have unique ID's. Instead, they rely on their
*name* as an identifier. For this reason, when exporting anything that needs to be linked
to the stratigraphic column, fmu-dataio will *change the name* to the official name as it
appears in the stratigraphic columns. The mechanism we use to do this, is a dictionary of all
horizons and zones, which we place into ``_stratigraphy.yml``.

The *key* of each entry is identical to the name used in RMS. There are two required
values: ``name`` (the official name as listed in the stratigraphic column) and 
``stratigraphic`` (True if stratigraphic level is listed in the stratigraphic columns, False if not).

In example below, observe that "TopVolantis" is a home-made name for ``VOLANTIS GP. Top`` 
and is in the stratigraphic column, while "Seabed" is not.

In addition, you may want to use some of the *optional* values:

    * ``alias`` is a list of known aliases for this stratigraphic entity.
    * ``stratigraphic_alias`` is a list of valid *stratigraphic* aliases for this entry, e.g. when a 
    * | specific horizon is the top of both a formation and a group, or similar.


From the Drogon tutorial:

.. code-block:: yaml
  
    # HORIZONS
    Seabed:
        stratigraphic: False # This horizon is NOT in the stratigraphic column.
        name: Seabed
    TopVolantis:
        stratigraphic: True # This horizon is in the stratigraphic column...
        name: VOLANTIS GP. Top # ...and this is what it is called.
        alias: # Optional
        - TopVOLANTIS
        - TOP_VOLANTIS
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

.. note::
  fmu-dataio will do validation of this configuration, and report to you if there are
  errors of any kind. Later, you will create a first script for exporting data, and you
  might see validation errors then if you have made mistakes here.


global_variables.yml | **model**
--------------------------------

Now we insert the ``model`` entry in ``global_variables.yml``.

``model`` block contains basic information about the model. According to the FMU standard,
all model setups should have a name and a revision. This is important information for
any usage of model results, and other systems such as REP will actively use this information
to render the data.

In the example below, you see how this is inserted. You also see that we have included
the three files we made above (``_masterdata.yml``, ``_access.yml`` and ``_stratigraphy.yml``)

.. note::
  The ``!include`` statement simply inserts contents from another file into the main
  yaml file. You could also put the contents directly into ``global_variables.yml``, but
  we encourage using ``!include`` to keep the main ``global_variables.yml`` somewhat tidy.


The global_variables.yml now looks like this:

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


**You are done with the first part!** We know this was boring and probably somewhat
confusing. The good news is that this is to a large degree a one-off thing, and you
should not expect to have to do this again and again. Perhaps never again!


Workflow for creating case metadata
-----------------------------------

It is time to create the ERT workflow which will generate case metadata. **Case metadata**
are metadata about the specific *case* you are running. A *case* in this context is a group
of one or more ensembles, which will appear in the same folder structure on /scratch.
Example: ``/scratch/<asset>/<user>/<CASE>/...``.

For each FMU case, a set of metadata is generated and stored on
/scratch/<case_directory>/share/metadata/fmu_results.yml. The case metadata are read by
individual export jobs, and, if you opt to upload data into Sumo, the case metadata are
used to register the case. Case metadata are made by a hooked (pre-sim) ERT workflow
running ``PRE_SIMULATION``.

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
    -- 
    -- NOTE! If using optional arguments, note that the "--" annotation will be interpreted
    --       as comments by ERT if not wrapped in quotes. This is the syntax to use:
    --       (existing arguments) "--sumo" "--sumo_env" dev

.. note::
    Note that there are references to Sumo in the script above. You don't have to worry
    about that for now.

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

What about Sumo?
~~~~~~~~~~~~~~~~

Odds are that you are implementing rich metadata export so that you can start utilizing
Sumo. Producing metadata with exported data is a pre-requisite for using Sumo. When you
have undertaken the steps above, you are good to go! Head to 
`Sumo <https://fmu-sumo.app.radix.equinor.com/>`_ and click "documentation" to
get going 👍
