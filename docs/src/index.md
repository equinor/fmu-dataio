# fmu-dataio documentation

**fmu-dataio** is a specialized library designed to streamline the export of
data from Fast Model Update (FMU) workflows. It simplifies the process of
exporting data in accordance with the FMU data standard while creating and
attaching relevant metadata.

In addition to export capabilities, fmu-dataio facilitates the retrieval of
data that has been exported and uploaded to cloud-based storage solutions,
such as Sumo, after the completion of an FMU experiment.

To learn how to use fmu-dataio,

- Get an [Overview](overview.md) of how it is used
- Then, [Get Started](getting_started.md) with some set up and your first
  exports

If you find bugs, need help, or want to talk to the developers, reach out via:

- [GitHub Issues](https://github.com/equinor/fmu-dataio/issues)
- `#fmu-dataio` on Slack
- The [FMU portal](https://fmu.equinor.com)

```{toctree}
:maxdepth: 2
:hidden:

overview.md
getting_started.md
simple_exports/index.md
custom_exports/index.md
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Developer Guides

contributing
update_schemas
schema_versioning
datamodel/index
dataio_3_migration
apiref/modules
```
