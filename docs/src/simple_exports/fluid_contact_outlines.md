# Initial fluid contact outlines

This exports modelled initial fluid contact outlines from within RMS.

Each fluid contact outline corresponds to a specific zone or a group of zones
that share a common fluid contact. They are polygons representing the outline
of the hydrocarbon-filled zone above a specific contact.

The fluid contact types supported is
- `fwl` (Free water level)
- `fgl` (Free gas level)
- `goc` (Gas-oil contact)
- `gwc` (Gas-water contact)
- `owc` (Oil-water contact)


:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | **{{ FluidContactOutlineSchema.VERSION }}** |
| Output | `share/results/maps/fluid_contact_outline/contactname/zonename.parquet` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- fluid contact outlines stored in the `General 2D data` folder within RMS.
- names of outlines defined in the `stratigraphy` block

A folder named `fluid_contact_outlines` must exist in the root of the `General
2D data` folder in RMS. This folder should contain at least one subfolder with
a valid fluid contact name (e.g., `fwl`, see the list above). The export
function will automatically process and export all outlines found within these
subfolders.

:::{note}
The names of the fluid contact outlines must be defined in the `stratigraphy`
block of the global configuration to enable mapping against masterdata.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.fluid_contact_outlines.export_fluid_contact_outlines
```

## Result

The fluid contact outlines from the `General 2D data` folder will be exported
as to `share/results/maps/fluid_contact_outline/contactname/zonename.parquet`.

This is a tabular file on `.parquet` format. It contains the following columns
with types validated as indicated.

```{eval-rst}
.. autopydantic_model:: fmu.datamodels.standard_result.fluid_contact_outline.FluidContactOutlineResultRow
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
| Version | {{ FluidContactOutlineSchema.VERSION }} |
| Filename | {{ FluidContactOutlineSchema.FILENAME }} |
| Path | {{ FluidContactOutlineSchema.PATH }} |
| Prod URL | {{ '[{}]({}) 🔒'.format(FluidContactOutlineSchema.prod_url(), FluidContactOutlineSchema.prod_url()) }}
| Dev URL | {{ '[{}]({}) 🔒'.format(FluidContactOutlineSchema.dev_url(), FluidContactOutlineSchema.dev_url()) }}

### JSON schema

The current JSON schema is embedded here.

{{ FluidContactOutlineSchema.literalinclude }}

## Load fluid contact outlines

The loader interface for fluid contact outlines standard results is still
under development and not supported yet.
