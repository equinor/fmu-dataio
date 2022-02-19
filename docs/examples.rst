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

Aggregated surface
-----------------------------------

When many realizations of the same data object are created, i.e. FMU level 4 and 5,
the results are represented by the *distribution* of objects it produces, e.g. across
all realizations. To effectively communicate, analyze, compare and visualize such
results they are aggregated into statistical representations of the distribution.

Aggregated surfaces are therefore representations of a distribution of surfaces,
typically in the form of new surfaces representing point-wise statistics of the input
realisations.


   Statistical surfaces are created by an aggregation service in some form, such as a 
   Python script collecting surfaces across all realizations of an ensemble, stacking
   their values and calculating statistics on each coordinate. For each coordinate,
   there will be one value per realization.
   
   E.g. the **mean** of

   - real1/mysurface
   - real2/mysurface
   - real2/mysurface
   - ...
   - realn/mysurface)

   = meansurface, which is a surface where each coordinate represent the **mean** value
   in this coordinate across the ensemble of realizations.

The example below show how fmu-dataio can be used to
1) Produce metadata for an existing aggregated surface, and/or
2) Produce metadata + export an aggregated surface to disk.

...in two different contexts:
1) Realisations are store on the disk (aka scratch disk pattern)
2) Realisations are stored in the cloud (aka Sumo pattern)

Creating metadata for aggregations is different compared to doing it for realizations.
The main difference is that while realization metadata are entirely made - aggregation
metadata take much of their attributes from the input surfaces. In fmu-dataio, the first
instance in the given list of source metadata will be used as a template.


Python script
~~~~~~~~~~~~~

.. literalinclude:: ../examples/s/d/nn/_project/aggregate_surfaces.py
   :language: python

|

   An aggregated surface usually belongs to a specific iteration of a specific case from
   an FMU run. It is made by a post-process which hooks across (usually) all
   realizations in an iteration/ensemble. From the FMU perspective, aggregations can be
   seen as a subtype of *post-processed* data.