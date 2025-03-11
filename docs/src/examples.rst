Examples
========

This is a collection of examples showing how fmu-dataio can be used in different contexts, 
and for different data types. The examples typically shows a Python script, together with a
corresponding metadata file that would be produced when running the script.

If working inside RMS we often retrieve RMS data from the project itself. In the
examples the syntax for that is commented out, but it is still shown so you
can comment it out in your code.

The global variables used here
------------------------------

This is a snippet of the ``global_variables.yml`` file which holds the static metadata described in the 
`previous section <./preparations.html>`__. In real cases this file will be much longer.

.. toggle::

   .. literalinclude:: ../../examples/realization-0/iter-0/fmuconfig/output/global_variables.yml
      :language: yaml

|

Exporting fault polygons
------------------------

Python script
~~~~~~~~~~~~~

.. literalinclude:: ../../examples/realization-0/iter-0/scripts/export_faultpolygons.py
   :language: python

Press + to see generated YAML file.

.. toggle::

   .. literalinclude:: ../../examples/realization-0/iter-0/share/results/polygons/.volantis_gp_top--faultlines.pol.yml
      :language: yaml

|

Exporting average maps from grid properties
-------------------------------------------

Python script
~~~~~~~~~~~~~

.. literalinclude:: ../../examples/realization-0/iter-0/scripts/export_propmaps.py
   :language: python


Press + to see generated YAML file for metadata.

.. toggle::

   .. literalinclude:: ../../examples/realization-0/iter-0/share/results/maps/.therys--average_porosity.gri.yml
      :language: yaml

|

Exporting 3D grids with properties
----------------------------------

Python script
~~~~~~~~~~~~~

.. literalinclude:: ../../examples/realization-0/iter-0/scripts/export_grid3d.py
   :language: python

Press + to see generated YAML files for metadata.


.. toggle::

   .. literalinclude:: ../../examples/realization-0/iter-0/share/results/grids/.geogrid.roff.yml
      :language: yaml

.. toggle::

   .. literalinclude:: ../../examples/realization-0/iter-0/share/results/grids/.geogrid--facies.roff.yml
      :language: yaml

|

Exporting volume tables RMS or file
-----------------------------------

Below is an example of exporting volume tables from csv-files, 
while an example of a simple export of RMS volumetrics can be found 
`here <https://fmu-dataio.readthedocs.io/en/latest/standard_results/initial_inplace_volumes.html>`.

Python script
~~~~~~~~~~~~~

.. literalinclude:: ../../examples/realization-0/iter-0/scripts/export_volumetables.py
   :language: python

.. toggle::

   .. literalinclude:: ../../examples/realization-0/iter-0/share/results/tables/.geogrid--volumes.csv.yml
      :language: yaml

|

Exporting a faultroom plugin result surface
-------------------------------------------

The FaultRoom plugin for RMS produces special json files that e.g. can be viewed with DynaGeo.


Python script
~~~~~~~~~~~~~

.. literalinclude:: ../../examples/realization-0/iter-0/scripts/export_faultroom_surfaces.py
   :language: python

.. toggle::

   .. literalinclude:: ../../examples/realization-0/iter-0/share/results/maps/volantis_gp_top--faultroom_d1433e1.json
      :language: yaml

|
