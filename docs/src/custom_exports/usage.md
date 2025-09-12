# Usage

Custom exports requires an instance of the
[`ExportData`](#fmu.dataio.ExportData) class. When creating an instance of
this class, some information must be provided, and this information is in part
dependent upon the type of data you are exporting.

The basic usage pattern is then:

1. Create an [`ExportData`](#fmu.dataio.ExportData) instance with relevant
   input values
2. Use the [`export(data)`](#fmu.dataio.ExportData.export) method to export
   data with it

The [`ExportData`](#fmu.dataio.ExportData) class can be imported like so:

```python
from fmu.dataio import ExportData
```

or,

```python
from fmu import dataio
# You can use dataio.ExportData directly
```

The following are the currently supported input values when creating an
instance of the [`ExportData`](#fmu.dataio.ExportData) class. They are ordered
first by whether or not they are required to create valid metadata, and also
by how frequently they are used.

After the [`ExportData`](#fmu.dataio.ExportData) instance has been created
with its initial values, those values cannot and should not be changed. This
means that whenever data that requires different values is being exported, a
new instance of [`ExportData`](#fmu.dataio.ExportData) must be created with
those different values.

Some data types (also referred to as
[_content_](#fmu.dataio.ExportData.content) types) place a requirement on
otherwise optional fields.

```{eval-rst}

.. autoclass:: fmu.dataio.ExportData
   :members:
   :exclude-members: __init__, generate_metadata, export
   :no-special-members:

```

## Exporting Data

After creating the [`ExportData`](#fmu.dataio.ExportData) instance, you can
then use the [`export()`](#fmu.dataio.ExportData.export) method to export data
with it.

```{eval-rst}

.. automethod:: fmu.dataio.ExportData.export

```

## Examples

Proceed to the [Examples](examples/index.md) section to see some complete
scripts which use [`ExportData`](#fmu.dataio.ExportData) to export custom
results.
