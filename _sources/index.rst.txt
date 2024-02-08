Welcome to FMU-dataio's documentation
=====================================

``fmu-dataio`` is a specialized Python library for managing data in Fast Model Update (FMU) workflows. 
It focuses on exporting data while adhering to the FMU standards, which include both file
and folder conventions, and rich metadata integration for various data consumers. The
library is designed for consistent usage across all stages of FMU workflows, including
ERT FORWARD_MODEL and pre-/post-processing jobs. ``fmu-dataio`` can be used both inside
and outside RMS.

The purpose of ``fmu-dataio`` is to **simplify** data export and to add **context** to data
produced by FMU workflows so that they can be used and understood also outside FMU. This
is fundamental for enabling usage of the vast amounts of data produced by FMU without
requiring significant manual intervention and repetitive work. The amount of context required
is not possible to fit in a filename alone. Hence, fmu-dataio produces and attaches rich metadata
to exported files.

In addition to the data export functions, ``fmu-dataio`` also contains the data model for
FMU results.

While ``fmu-dataio`` represents a fair amount of simplification on its own, it is also
a necessary investment for tapping into more simplification possibilities, such as management
of results in Sumo, automated data pipelines to the Reservoir Experience Platform, centralized
post-processing services, new and improved cloud-only version of Webviz and much more.


.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: About

   installation
   contributing

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: User Guide and Reference

   overview
   preparations
   examples
   apiref/modules
   datamodel
   datastructure


