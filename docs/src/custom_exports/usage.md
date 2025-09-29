# Usage

Custom exports require an instance of the
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

### Supported Data Objects

fmu-dataio supports exporting most fundamental data types and objects used in
reservoir modelling.

The following Python objects are supported by fmu-dataio. This means they can
be passed to the [`export()`](#fmu.dataio.ExportData.export) method on an
appropriately configured instance of [`ExportData`](#fmu.dataio.ExportData).

#### xtgeo

The following [xtgeo](https://xtgeo.readthedocs.io/) objects can be exported
by fmu-dataio.  Currently, this is all xtgeo types except for wells. These
objects are documented in the [xtgeo
documentation](https://xtgeo.readthedocs.io).

- [xtgeo.RegularSurface](https://xtgeo.readthedocs.io/en/stable/datamodels.html#surface-regularsurface).
  Exported as `.gri` files.
- [xtgeo.Polygons](https://xtgeo.readthedocs.io/en/stable/datamodels.html#xyz-data-points-and-polygons).
  Exported as `.csv` files by default.
- [xtgeo.Points](https://xtgeo.readthedocs.io/en/stable/datamodels.html#xyz-data-points-and-polygons)
  Exported as `.csv` files by default.
- [xtgeo.Cube](https://xtgeo.readthedocs.io/en/stable/datamodels.html#cube-data)
  Exported as `.segy` files.
- [xtgeo.Grid](https://xtgeo.readthedocs.io/en/stable/datamodels.html#d-grid-and-properties)
  Exported as `.roff` files.
- [xtgeo.GridProperty](https://xtgeo.readthedocs.io/en/stable/datamodels.html#d-grid-and-properties)
  Exported as `.roff` files.

#### Pandas Dataframes

[Pandas
dataframes](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html)
representing tabular/csv data can be exported. This is the most common way to
export tabular data.

Dataframes are exported as `.csv` files by default.

#### PyArrow Tables

[PyArrow
tables](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html)
representing tabular/csv data can be exported.

PyArrow tables are exported as `.parquet` files.

#### Python Dictionaries

Python dictionaries containing structured data can be exported as well. This
should be the last-case scenario, i.e. used only when other pre-defined data
types do not meet your needs.

Python dictionaries are exported as JSON files.

#### FaultRoom Surfaces

FaultRoom is an RMS plugin used in some FMU workflows. FaultRoom surfaces are
GeoJSON files that can be created and exported by the FaultRoom plugin and
have a particular format that is understood by fmu-dataio.

FaultRoom surfaces are exported as JSON files.

#### GOCAD Surface/TSURF Files

These are triangle-based surfaces. Within FMU, TSURF files can be created and
exported within RMS. The `TSurfData` class is currently stored in fmu-dataio
but will eventually exist as an xtgeo type.

TSURF files are exported as `.ts` TSURF files.

#### Something Missing?

If you have a particular data type you would like to export with fmu-dataio,
but it is not supported, please reach out via:

- [GitHub Issues](https://github.com/equinor/fmu-dataio/issues)
- `#fmu-dataio` on Slack
- The [FMU portal](https://fmu.equinor.com)

## Examples

Proceed to the [Examples](examples/index.md) section to see some complete
scripts which use [`ExportData`](#fmu.dataio.ExportData) to export custom
results.
