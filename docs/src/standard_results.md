# Standard results

Standard results are results exported from FMU workflows according to strict standards. They are validated and consumers can expect consistency and stability.

## Export of standard results
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

### Load standard results
In addition to the functions for export of standard results to Sumo, fmu-dataio
also exposes functions for loading standard results from Sumo. The purpose of
these loaders is to offer functionality to the user to load the standard results they
have exported during an Ert run back into their code in RMS, or to local scripts or tools like
Jupyter notebook for post-processing, analysis and visualization. 

The standard result loaders aim to offer an interface to interact with the exported 
standard results through fmu-dataio, providing methods to load the standard results in a user friendly
format or storing them to disk.

Each standard result export function has a corresponding load function. The load functions returns
a loader object for a given ensemble, providing methods to interact with the standard results data
in that ensemble, e.g. getting the data object(s) for a specific realization or store the data to disk.

### Using fmu-dataio to export and load standard results
```{toctree}
:maxdepth: 2
:glob:
:titlesonly:

standard_results/*
```
