# Custom Exports

As mentioned in the [Overview](../overview.md), **custom exports** are exports
that may be more flexible in the way that data is exported compared to [simple
exports](../simple_exports/index.md). Custom exports produce **custom
results**.

Custom exports undergo less validation than simple exports. As a result of
this, custom results are _less flexible_ in their utility outside of FMU, but
may be more useful for customized workflows.

## Key Features

### Pros

- Export what you want, how you want [^*]
- More opportunity to pre-process data before export
- More choices in exported data type

[^*]: Custom exports **do** have limitations and apply some validation. Over
  time this validation may become more strict to prevent obviously incorrect
  data.

### Cons

- More complicated to use
- Less utility and support outside of FMU
- Less support for retrieving uploaded data
- Do not automatically adhere to the FMU data standard

## Usage

Custom exports require using a class provided by fmu-dataio called
`ExportData`. As shown in the [Overview](../overview.md), in its most
simplistic form it is used like so:

```python
from fmu.dataio import ExportData

df = create_data() # Some function that creates a Pandas dataframe
cfg = get_global_config() # The FMU global configuration

# ExportData can take many arguments. This is a simplified example.
exp = ExportData(
    config=cfg,
    content="volumes",
)
exp.export(df) # Exports the Pandas dataframe as a csv by default
```

To learn more about how to use the `ExportData` class, proceed to the [Custom
Exports Usage](usage.md) section.

If you want to jump straight into some examples, check out the [Custom Exports
Examples](examples/index.md) section.

```{toctree}
:maxdepth: 2
:hidden:

usage.md
examples/index.md
```
