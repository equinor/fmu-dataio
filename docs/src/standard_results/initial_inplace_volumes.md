# Initial inplace volumes

This exports the initial inplace volumes of a single grid from within RMS.

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | **{{ InplaceVolumesSchema.VERSION }}** |
| Output | `share/results/tables/volumes/gridname.parquet` |
:::

## Requirements

- RMS
- RMS volumetrics job stored to report table
- Proper grid erosion

Inplace volumes for grids in RMS should always be computed in a **single** RMS
volumetrics job, and the result should be stored as a report table inside RMS.
The simplified export function will use the RMS API behind the scene to
retrieve this table, and all necessary data needed for `fmu.dataio`.

The performance of the volumetrics jobs in RMS has greatly improved from the
past, now typically representing the fastest method for calculating in-place
volumes. However, it is important to note that generating output maps, such as
Zone maps, during the volumetrics job can significantly decelerate the process.

:::{note}
Some assets are using erosion multipliers as a means to reduce the bulk
and pore volume, instead of performing actual erosion by cell removal in the
grid. This is not supported, and proper grid erosion is required. If the erosion
multiplier is important for flow simulation, the erosion and volumetrics job
should be moved to after the export for flow simulation.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.inplace_volumes.export_inplace_volumes
```

## Result

Given a grid model name `Geogrid` the result file will be
`share/results/tables/volumes/geogrid.parquet`.

This is a tabular file that can be converted to `.csv` or similar. It contains
the following columns with types validated as indicated.

```{eval-rst}
.. autopydantic_model:: fmu.dataio._models.standard_result.inplace_volumes.InplaceVolumesResultRow
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

This standard results is made available with a validation schema that can be
used by consumers. A reference to the URL where this schema is located is
present within the `data.standard_result` key in its associated object metadata.

| Field | Value |
| --- | --- |
| Version | {{ InplaceVolumesSchema.VERSION }} |
| Filename | {{ InplaceVolumesSchema.FILENAME }} |
| Path | {{ InplaceVolumesSchema.PATH }} |
| Prod URL | {{ '[{}]({}) 🔒'.format(InplaceVolumesSchema.prod_url(), InplaceVolumesSchema.prod_url()) }}
| Dev URL | {{ '[{}]({}) 🔒'.format(InplaceVolumesSchema.dev_url(), InplaceVolumesSchema.dev_url()) }}

### JSON schema

The current JSON schema is embedded here.

{{ InplaceVolumesSchema.literalinclude }}
