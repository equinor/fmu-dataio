fmu-dataio 3.0 migration guide
==============================

This document contains a set of instructions on how to update your code to work
with ``fmu-dataio`` 3.0. Almost all changes that have taken place are related to 
fmu-dataio's ``ExportData`` class.


ExportData
----------
Changes to input arguments  
^^^^^^^^^^^^^^^^^^^^^^^^^^
The following arguments are deprecated, or have specific input types/values that are deprecated, 
but with replacements inplace.

 - ``access_ssdl`` is deprecated and replaced by the ``classification`` and ``rep_include`` arguments.
 - ``classification='asset'`` is deprecated, use ``classification='restricted'`` instead.
 - ``fmu_context='preprocessed'`` is deprecated, use argument ``preprocessed=True`` instead.
 - ``vertical_domain`` now only supports string input with value either ``time`` / ``depth``. Using 
   a dictionary form to provide a reference together with the ``vertical_domain`` is deprecated, use 
   the ``domain_reference`` argument instead.
 - ``workflow`` now only supports string input, example ``workflow='Structural modelling'``.
 - ``content`` was previously optional, it should now be explicitly provided.
 - ``content={'seismic': {'offset': '0-15'}}`` no longer works, use the key ``stacking_offset`` instead 
   of ``offset``.


Following are an example demonstrating several deprecated patterns:

.. code-block:: python

    from fmu.dataio import ExportData

    ExportData(
        fmu_context='preprocessed', # ⛔️ 
        access_ssdl={'access_level': 'asset', 'rep_include': True}, # ⛔️ 
        vertical_domain={'depth': 'msl'}, # ⛔️ 
        workflow={'reference': 'Structural modelling'}, # ⛔️ 
    )

Change to this instead 👇:

.. code-block:: python

    from fmu.dataio import ExportData

    ExportData(
        content='depth', # ✅ content must explicitly be provided
        preprocessed=True, # ✅
        classification='restricted', # ✅ note the use of 'restricted' instead of 'asset'
        rep_include=True, # ✅
        vertical_domain='depth', # ✅
        domain_reference='msl', # ✅
        workflow='Structural modelling', # ✅
    )


The following arguments are deprecated, and have for a long time not had any effect. 
They can safely be removed.

 - ``depth_reference`` is deprecated and was never used, use the new ``domain_reference`` argument instead.
 - ``runpath`` is deprecated and picked up by ERT variables instead.
 - ``reuse_metadata_rule`` never had more than one option, and is now deprecated.
 - ``grid_model`` was intended to be used for linking a grid_property to a grid, this is now done through 
   the ``geometry`` argument instead.
 - ``realization`` is deprecated, realization number is automatically picked up from environment variables.
 - ``verbosity`` is deprecated, logging level should be set from client script in a standard manner instead.


The following arguments will be required if specific data types are exported.

 - ``geometry`` needs to be set if the object is of type ``xtgeo.GridProperty`` (see example  
   `here <https://fmu-dataio.readthedocs.io/en/latest/examples.html#exporting-3d-grids-with-properties>`_).


Additionally

 - ``fmu_context='case_symlink_realization'`` is no longer a valid argument value for ``fmu_context``.  
   If necessary to create symlinks from data stored at case level to the individual realizations, 
   use the ``SYMLINK`` forward model provided by ERT instead.


Changes to class variables 
^^^^^^^^^^^^^^^^^^^^^^^^^^
The following class variables are deprecated. For a while they've had no effect and can 
safely be removed if present in the code.

 * ``ExportData.allow_forcefolder_absolute`` 
 * ``ExportData.createfolder`` 
 * ``ExportData.include_ertjobs`` 
 * ``ExportData.legacy_time_format`` 
 * ``ExportData.table_include_index`` 
 * ``ExportData.verifyfolder`` 
 * ``ExportData.meta_format`` 


.. code-block:: python

    from fmu.dataio import ExportData
    
    surface = xtgeo.surface_from_file('mysurf.gri')

    exd = ExportData(
        config=CFG,
        content='depth',
        tagname='DS_final',
    )
    exd.legacy_time_format = True # ⛔️ no longer allowed, simply remove the line!
    exd.export(surface)


Providing arguments through export() / generate_metadata()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It is no longer possible to enter arguments inside the ``export()`` and ``generate_metadata()`` methods 
to update the ExportData instance after creation. These methods now only accepts the object to export.
To get your code running simply move your arguments from the methods up to the initialisation of the 
ExportData instance, or if necessary create a new instance of the ExportData class.


Example with deprecated pattern:

.. code-block:: python

    from fmu.dataio import ExportData
    
    surface = xtgeo.surface_from_file('mysurf.gri')

    exd = ExportData(config=CFG)
    exd.export(
        surface,      
        content='depth',    # ⛔️ no longer allowed!
        tagname='DS_final'  # ⛔️ no longer allowed!
    )

Change to this instead 👇:

.. code-block:: python

    from fmu.dataio import ExportData
    
    surface = xtgeo.surface_from_file('mysurf.gri')

    exd = ExportData(
        config=CFG,
        content='depth',     # ✅
        tagname='DS_final',  # ✅
    )
    exd.export(surface)

Note if you have a loop it might be necessary to move the creation of the 
ExportData instance inside the loop. Example below:

.. code-block:: python

    from fmu.dataio import ExportData
    
    SURFACE_FOLDER = 'TS_final'
    SURFACES = ['TopVolantis', 'TopVolon']

    def export_surfaces():    

      exd = ExportData(
          config=CFG,          
          content='time',
          tagname=SURFACE_FOLDER,
      )
        
      for surf_name in SURFACES:
          surface = xtgeo.surface_from_roxar(project, surf_name, SURFACE_FOLDER)
          exd.export(surface, name=surfname)    # ⛔️ no longer allowed!   
          

Change to this instead 👇:

.. code-block:: python

    from fmu.dataio import ExportData
    
    SURFACE_FOLDER = 'TS_final'
    SURFACES = ['TopVolantis', 'TopVolon']

    def export_surfaces():    

      for surf_name in SURFACES:
          surface = xtgeo.surface_from_roxar(project, surf_name, SURFACE_FOLDER)

          exd = ExportData(
              config=CFG,          
              content='time',
              tagname=SURFACE_FOLDER,
              name=surfname,
          )
          exd.export(surface)   


Additionally 

 - The ``return_symlink`` argument to ``export()`` is deprecated. It is redundant and can be removed.
 - The ``compute_md5`` argument to ``generate_metadata()`` is deprecated and can be removed, as 
   an MD5 checksum is always computed by default.


Getting partial metadata from generate_metadata() when config is invalid
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It was previously possible to get partial metadata from ``generate_metadata()``
when the global config file was invalid. This partial metadata was not valid according
to the datamodel and could not be uploaded to Sumo. Creating invalid metadata is no
longer supported, if the config is invalid an empty dictionary is returned instead.


Providing settings through environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It was previously possible to have a yml-file specifying global input arguments to 
the ``ExportData`` class, and have an environment variable ``FMU_DATAIO_CONFIG`` pointing
to that file. This is no longer possible and it will have no effect if provided.


Using ExportData to re-export preprocessed data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Using the ``ExportData`` class for re-exporting preprocessed data is deprecated. Use the dedicated 
``ExportPreprocessedData`` class instead. Main difference being that the config is no longer needed 
as input argument, and redundant arguments are no longer accepted.


Exaple using ``ExportData`` to re-export preprocessed data:

.. code-block:: python

    from fmu.dataio import ExportData
    from fmu.config import utilities as utils

    config = utils.yaml_load('../../fmuconfig/output/global_variables.yml')

    preprocessed_seismic_cube = 'share/preprocessed/cubes/mycube.segy'

    exd = ExportData(
        config=config,
        is_observation=True, 
        casepath='/scratch/fmu/user/mycase',
    )
    exd.export(preprocessed_seismic_cube)


Exaple using ``ExportPreprocessedData`` to re-export preprocessed data:

.. code-block:: python

    from fmu.dataio import ExportPreprocessedData
    
    preprocessed_seismic_cube = 'share/preprocessed/cubes/mycube.segy'

    exd = ExportPreprocessedData(
        is_observation=True, 
        casepath='/scratch/fmu/user/mycase',
    )
    exd.export(preprocessed_seismic_cube)

.. note::
  Preprocessed data refers to data that have previously been exported with the ``ExportData`` class, 
  i.e. it contains metadata and are stored in a ``share/preprocessed/`` folder typically on the project disk.


Changes affecting the global_variables.yml
------------------------------------------
The ``access.ssdl`` block is deprecated, it is recommended to remove it entirely. Setting a global 
classification for all your export jobs should now be done through the ``access.classification`` field 
instead. Furthermore, setting a global ``rep_include`` value for all exports is no longer supported. 
Instead, you must set it on a per-object basis using the ``rep_include`` argument in the ``ExportData`` instance.


Example of an old set-up:

.. code-block:: yaml

    global:
      access:
        asset:
          name: Drogon
        ssdl:
          access_level: internal # ⛔️ no longer allowed
          rep_include: true  # ⛔️ no longer in use, simply remove the line!


Example of a new set-up:

.. code-block:: yaml

    global:
      access:
        asset:
          name: Drogon
        classification: internal # ✅ Correct way of entering security classification

.. note::
  If the config contains both ``access.ssdl.access_level`` (deprecated) and ``access.classification``.
  The value from ``access.classification`` will be used.



AggregatedData
--------------
Changes to input arguments  
 - ``verbosity`` is deprecated, logging level should be set from client script in a standard manner instead.

Changes to method arguments  
 - The ``skip_null`` argument to ``generate_metadata()`` is deprecated. It is redundant and can be removed.
 - The ``compute_md5`` argument to ``generate_metadata()`` is deprecated and can be removed, as 
   an MD5 checksum is always computed by default.
   
Deprecated methods
 - The ``generate_aggregation_metadata()`` method is deprecated. Replace it with the identical 
   ``generate_metadata()`` method instead.

Deprecated class variables 
 * ``AggregatedData.meta_format`` - metadata will always be exported in yaml format
