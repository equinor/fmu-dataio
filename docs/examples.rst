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

   .. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/share/results/polygons/.volantis_gp_top--faultlines.pol.yml
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

   .. literalinclude:: ../examples/s/d/nn/xcase/realization-0/iter-0/share/results/grids/.facies.roff.yml
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

Using fmu-dataio for post-processed data
----------------------------------------

The example below show how fmu-dataio can be used in a post-processing context, here in a
surface aggregation example.

When using ensemble-based methods for probabilistic modelling, the result is represented
by the distribution of the realizations, not by the individual realizations themselves.
In such a context, easy access to statistical representations of the ensemble is important.
For surfaces, this typically includes point-wise mean, std, min/max, p10/p90 and others.

Aggregations in an FMU context is usually done by standalone Python scripts, but cloud
services are also in the making (Sumo). The example below show how fmu-dataio can be used
to simplify an existing aggregation service, as well as make de-centralized methods more
robust by centralizing the definitions and handling of metadata.

.. note::
   It is common that surfaces exported from RMS or other sources have undefined areas.
   For some surfaces, typically various thickness surfaces (e.g. HCPV thickness from RMS
   volumetric jobs), undefined values shall be treated as zero (0.0) when included in 
   statistical calculations. Therefore, when exporting surfaces of this type, set the 
   `undef_is_zero` flag to `True` when exporting. This tells later consumers of the 
   surface that they should handle `UNDEF` as zero.


Python script
~~~~~~~~~~~~~

.. literalinclude:: ../examples/s/d/nn/_project/aggregate_surfaces.py
   :language: python

|
