# Standard result exports

fmu-dataio exposes functions for the export of standard results. These are
_standardized data_ that must conform to particular data shapes defined in
this package. Data being exported with these functions undergoes strict
validation.

The purpose of this strictness is to give data quality guarantees. When data
is validated against a particular form, i.e., it is validated against a schema
defined in this package, it is simpler for consumer applications to provide
support for visualization, aggregation, etc.

This documentation is oriented toward someone who might be implementing these
functions within a model. If you are a consumer you might find the Sumo
documentation more helpful. Some of the documentation here is duplicated
there.

```{note}
All simplified export functions requires that the global configuration file is
found at the standard location in FMU. For RMS exports that will be
`'../../fmuconfig/output/global_variables.yml'`
```

```{toctree}
:maxdepth: 2
:glob:
:titlesonly:
:caption: Standard results

standard_results/*
```
