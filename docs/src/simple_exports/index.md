# Simple Exports

As mentioned in the [Overview](../overview.md) section, **simple exports** are
functions defined in fmu-dataio that export **standard results**. A **standard
result** is exported data that adheres to the FMU data standard.

## Key Features

- Simple to use functions
- Strict input arguments and output data
- Validation of data at export
- Used for non-FMU services like REP, DynaGeo, and more
- Simple loaders to retrieve data from Sumo

## Current Standard Results

Below are the currently supported standard results. These pages provide
detailed information on where, how, and when to use the export function, as
well as how to use the corresponding simple loader.

```{admonition} In Development
:class: important
Standard results are still in development. This list will continue to grow
over time as new standard results are added. For exporting other types of
data, check out the [Custom Exports](../custom_exports/index.md) section.
```

```{toctree}
:maxdepth: 2
:glob:
:titlesonly:

*
!index.md
```

## When to use

Simple exports are the **recommended** way to export data. Simple exports
provide consistency and data quality guarantees so that this data can be used
in a uniform manner for visualization, aggregation, analysis, and more.

Simple exports **do not** limit your ability to export data in a customized,
non-standard way. Standard results from simple exports can be seen as results
from FMU as a system, rather than results from a specific FMU workflow.

This means that the best practice is to implement simple exports to maximize
the utility of your exported data. For more local and personalized needs you
can use [Custom exports](../custom_exports/index.md) in addition to them.

## Simple Loaders

Paired to simple exports are **simple loaders**. Simple loaders are functions
that enable you to retrieve standard results from Sumo _after_ an experiment
has ended. This will allow you to load and use data in local scripts, tools,
or Jupyter notebooks for post-processing, analysis, and visualization, in a
simple manner.

This functionality is currently only available for standard results.

## Custom Exports

The number of standard results is still growing and many types of data do not
have a simple exporter yet. For all other data, you will need to use [Custom
Exports](../custom_exports/index.md).
