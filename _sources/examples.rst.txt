Examples
========

In the following is a list of examples you can study and copy.

First is a snippet of the ``global_variables.yml`` file which holds the static
metadata. In real cases this file will be much longer.

Then there are several examples for various datatypes. In general there is a python
script, and next is an example from a metadata file that is produced by
the script.

If working inside RMS we often retrieve RMS data from the project itself. In the
examples the syntax for that is commented out, but it is still shown so you
can comment it out in your code.

The global variables used here
------------------------------

Here are the relevant sections in the global variables (output) file (press plus to
expand):

.. toggle::

   .. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/fmuconfig/output/global_variables.yml
      :language: yaml

|

Exporting fault polygons
------------------------

Python script
~~~~~~~~~~~~~

.. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/rms/bin/export_faultpolygons.py
   :language: python

Press + to see generated YAML file.

.. toggle::

   .. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/share/results/polygons/.topvolantis--faultlines.pol.yml
      :language: yaml

|

Exporting average maps from grid properties
-------------------------------------------

Python script
~~~~~~~~~~~~~

.. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/rms/bin/export_propmaps.py
   :language: python


Press + to see generated YAML file for metadata.

.. toggle::

   .. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/share/results/maps/.therys--average_porosity.gri.yml
      :language: yaml

|

Exporting 3D grids with properties
----------------------------------

Python script
~~~~~~~~~~~~~

.. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/any/bin/export_grid3d.py
   :language: python

Press + to see generated YAML files for metadata.


.. toggle::

   .. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/share/results/grids/.geogrid.roff.yml
      :language: yaml

.. toggle::

   .. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/share/results/grids/.geogrid--facies.roff.yml
      :language: yaml

|

Exporting volume tables RMS or file
-----------------------------------

Python script
~~~~~~~~~~~~~

.. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/any/bin/export_volumetables.py
   :language: python

.. toggle::

   .. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/share/results/tables/.geogrid--volumes.csv.yml
      :language: yaml

|
