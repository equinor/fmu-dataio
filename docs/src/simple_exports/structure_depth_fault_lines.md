# Structure depth fault lines

This exports the modelled structural depth fault lines from within RMS. These
fault lines are polygons that represent the intersection of a modelled
stratigraphic horizon surface with the modelled fault surfaces.

:::{note}
It is only possible to export **one single set** of depth fault lines per
model workflow, i.e. one fault line polygon object per stratigraphic horizon.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | **{{ StructureDepthFaultLinesSchema.VERSION }}** |
| Output | `share/results/polygons/structure_depth_fault_lines/surfacename.parquet` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- depth fault line polygons stored in a horizon folder within RMS

The fault line polygons must be located within a horizon folder in RMS and be
in domain `depth`. This export function will automatically export all
non-empty polygon objects from the provided folder.

:::{important}
These polygons should be extracted from the final depth horizon model using
the `Extract Fault Lines` job in RMS. This will ensure that all fault polygons
are closed and that the fault name is added as an attribute.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.structure_depth_fault_lines.export_structure_depth_fault_lines
```

## Result

Given a stratigraphic horizon name `TopVolantis` the result file will be
`share/results/polygons/structure_depth_fault_lines/topvolantis.parquet`.

This is a tabular file on `.parquet` format. It contains the following columns
with types validated as indicated.

```{eval-rst}
.. autopydantic_model:: fmu.datamodels.standard_result.structure_depth_fault_lines.StructureDepthFaultLinesResultRow
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
| Version | {{ StructureDepthFaultLinesSchema.VERSION }} |
| Filename | {{ StructureDepthFaultLinesSchema.FILENAME }} |
| Path | {{ StructureDepthFaultLinesSchema.PATH }} |
| Prod URL | {{ '[{}]({}) 🔒'.format(StructureDepthFaultLinesSchema.prod_url(), StructureDepthFaultLinesSchema.prod_url()) }}
| Dev URL | {{ '[{}]({}) 🔒'.format(StructureDepthFaultLinesSchema.dev_url(), StructureDepthFaultLinesSchema.dev_url()) }}

### JSON schema

The current JSON schema is embedded here.

{{ StructureDepthFaultLinesSchema.literalinclude }}

## Load structure depth fault lines

The loader interface for structure depth fault lines standard results is still
under development and not supported yet.
