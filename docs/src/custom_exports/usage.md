# Usage

Custom exports require an instance of the `ExportData` class. When creating an
instance of this class, some information must be provided, and this
information is in part dependent upon the type of data you are exporting.

The basic usage pattern is then:

1. Create an `ExportData` instance with relevant input values
2. Use the `export(data)` function to export data with it

The `ExportData` class can be imported like so:

```python
from fmu.dataio import ExportData
```

or,

```python
from fmu import dataio
# You can use dataio.ExportData directly
```

The following are the currently supported input values when creating an
instance of the `ExportData` class. They are ordered first by whether or not
they are required to create valid metadata, and also by how frequently they
are used.

Some data types (also referred to as _content_ types) place a requirement on
otherwise optional fields.

```{eval-rst}

.. autoclass:: fmu.dataio.ExportData
   :members:
   :exclude-members: __init__, generate_metadata, export
   :no-special-members:

```

## Exporting Data

After creating the `ExportData` instance, you can then use the `export()` method
to export data with it.

```{eval-rst}

.. automethod:: fmu.dataio.ExportData.export

```

## Examples

Proceed to the [Examples](examples/index.md) section to see some complete
scripts which use `ExportData` to export custom results.
