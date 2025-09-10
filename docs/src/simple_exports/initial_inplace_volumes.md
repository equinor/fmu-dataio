# Initial inplace volumes

This exports the initial inplace volumes of a single grid from within RMS.

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | **{{ InplaceVolumesSchema.VERSION }}** |
| Output | `share/results/tables/inplace_volumes/gridname.parquet` |
| Security classification | 🔴 Restricted |
:::

## Requirements

- RMS (minimum version 14.2)
- RMS volumetrics job stored to report table
- Proper grid erosion

Inplace volumes for grids in RMS should always be computed in a **single** RMS
volumetrics job, and the result should be stored as a report table inside RMS.
The simplified export function will use the RMS API behind the scene to
retrieve this table, and all necessary data needed for `fmu.dataio`.

The performance of the volumetrics jobs in RMS has greatly improved from the
past, now typically representing the fastest method for calculating in-place
volumes. However, it is important to note that generating output maps, such as
Zone maps, during the volumetrics job can significantly decelerate the
process.

:::{note}
Some assets are using erosion multipliers as a means to reduce the bulk and
pore volume, instead of performing actual erosion by cell removal in the grid.
This is not supported, and proper grid erosion is required. If the erosion
multiplier is important for flow simulation, the erosion and volumetrics job
should be moved to after the export for flow simulation.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.inplace_volumes.export_inplace_volumes
```

## Result

The volumetric table from RMS undergoes a couple of transformations to adhere
to the `inplace_volumes` standard format:

1. Water zone bulk and pore volumes are calculated by subtracting oil and gas
   zone volumes from the total volumes. The total volumes are removed, and any
   negative values caused by precision issues in RMS are truncated to zero.
2. The fluid-specific columns are unfied into a single set of volumetric
   columns, with an additional `FLUID` column indicating the fluid type. If
   the `NET` column is absent, it is set equal to the `BULK` column, assuming
   a net-to-gross ratio of one.

Given a grid model name `Geogrid` the result file will be
`share/results/tables/inplace_volumes/geogrid.parquet`.

This is a tabular file that can be converted to `.csv` or similar. It contains
the following columns with types validated as indicated.

```{eval-rst}
.. autopydantic_model:: fmu.datamodels.standard_results.inplace_volumes.InplaceVolumesResultRow
   :members:
   :inherited-members: BaseModel
   :model-show-config-summary: False
   :model-show-json: False
   :model-show-validator-members: False
   :model-show-validator-summary: False
   :field-list-validators: False
```

```{note}
The payload may contain other columns than the standard columns listed above.
However, when these columns are present, their type is validated.
```

## Standard result schema

This standard result is made available with a validation schema that can be
used by consumers. A reference to the URL where this schema is located is
present within the `data.standard_result` key in its associated object
metadata.

| Field | Value |
| --- | --- |
| Version | {{ InplaceVolumesSchema.VERSION }} |
| Filename | {{ InplaceVolumesSchema.FILENAME }} |
| Path | {{ InplaceVolumesSchema.PATH }} |
| Prod URL | {{ '[{}]({}) 🔒'.format(InplaceVolumesSchema.prod_url(), InplaceVolumesSchema.prod_url()) }}
| Dev URL | {{ '[{}]({}) 🔒'.format(InplaceVolumesSchema.dev_url(), InplaceVolumesSchema.dev_url()) }}

### Changelog

{{ InplaceVolumesSchema.VERSION_CHANGELOG }}

### JSON schema

The current JSON schema is embedded here.

{{ InplaceVolumesSchema.literalinclude }}

## Load initial inplace volumes

Use the below loader function, loader object and interface to load and
interact with the exported initial inplace volumes standard results.

```{hint}
For more information about the purpose of these loader functions, see [Loading
Data](../overview.md#loading-data) in the [Overview](../overview.md).
```

### Usage

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.load_inplace_volumes
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.InplaceVolumesLoader
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.InplaceVolumesLoader.list_realizations
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.InplaceVolumesLoader.get_realization
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.InplaceVolumesLoader.get_blobs
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.InplaceVolumesLoader.save_realization
```
