# Field outline

This exports the modelled field outline from within RMS. This field outline
is a polygon representing the outline of the hydrocarbon-filled reservoir
under initial conditions.

The field outline is typically calculated as the intersection between the
modelled top reservoir surface (in depth) and the fluid contact surface. Some
assets may choose to further refine the outline by limiting it to areas with
`net` reservoir properties. It is up to each asset to decide which definition
best suits their field.

The primary use case for the field outline is visualization. Unlike the
deterministic outlines from NPD, it is derived directly from the reservoir
model, providing greater precision, alignment with recent data, and
adaptability to the unique structure and fluid contact of each realization.

:::{note}
It is only possible to export **one** field outline object per model workflow.
For exporting outlines specific to different fluid types and zones, the
`fluid_contact_outline` standard result should be used instead.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | **{{ FieldOutlineSchema.VERSION }}** |
| Output | `share/results/polygons/field_outline/field_outline.parquet` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- a field outline polygon stored in the `General 2D data` folder within RMS.

The field outline polygon object must be named `field_outline` and be located
within the root of the `General 2D data` folder in RMS.

The export function will ensure that the polygon object consists of closed
polygons before proceeding with the export.


## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.field_outline.export_field_outline
```

## Result

The result file will be
`share/results/polygons/field_outline/field_outline.parquet`.

This is a tabular file on `.parquet` format. It contains the following columns
with types validated as indicated.

```{eval-rst}
.. autopydantic_model:: fmu.datamodels.standard_result.field_outline.FieldOutlineResultRow
   :members:
   :inherited-members: BaseModel
   :model-show-config-summary: False
   :model-show-json: False
   :model-show-validator-members: False
   :model-show-validator-summary: False
   :field-list-validators: False
```


## Standard result schema

This standard result is made available with a validation schema that can be
used by consumers. A reference to the URL where this schema is located is
present within the `data.standard_result` key in its associated object
metadata.

| Field | Value |
| --- | --- |
| Version | {{ FieldOutlineSchema.VERSION }} |
| Filename | {{ FieldOutlineSchema.FILENAME }} |
| Path | {{ FieldOutlineSchema.PATH }} |
| Prod URL | {{ '[{}]({}) 🔒'.format(FieldOutlineSchema.prod_url(), FieldOutlineSchema.prod_url()) }}
| Dev URL | {{ '[{}]({}) 🔒'.format(FieldOutlineSchema.dev_url(), FieldOutlineSchema.dev_url()) }}

### JSON schema

The current JSON schema is embedded here.

{{ FieldOutlineSchema.literalinclude }}

## Load field outlines

Use the below loader function, loader object, and interface to load and
interact with the exported field outlines standard results.

```{hint}
For more information about the purpose of these loader functions, see [Loading
Data](../overview.md#loading-data) in the [Overview](../overview.md).
```

### Usage
```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.load_field_outlines
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FieldOutlinesLoader
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FieldOutlinesLoader.list_realizations
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FieldOutlinesLoader.get_realization
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FieldOutlinesLoader.get_blobs
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FieldOutlinesLoader.save_realization
```
