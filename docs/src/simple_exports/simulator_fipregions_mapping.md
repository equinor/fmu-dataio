# Simulator fipregions mapping

This creates a `FIPNUM` property within a grid model in RMS and exports the
corresponding `zone / region` mappings as a standard result
`simulator_fipregions_mapping`.

The flow simulator uses `FIPNUM` as its standard region property to generate
reports on volumes and pressures for each `FIPNUM` value. The `FIPNUM` property
created by this functionality will have a unique value per `zone / region`
combination, which is the recommended standard. Reporting at a fine resolution
allows for combining data at coarser levels in analysis tools, while enabling
detailed investigations at a finer level.

:::{hint}
Use the same zone and region properties as in your volumetrics job for easy comparison
of initial volumes from the dynamic simulation against static inplace volumes.
:::

:::{note}
 Many existing workflows may have a `FIPNUM` definition that does not conform to the
 standard of having one unique value per `zone / region` combination. If you need to
 retain the current `FIPNUM` definition also, it should be renamed to a different
 `FIP` identifier (e.g., `FIPXXX`) and exported for the flow simulation.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/tables/simulator_fipregions_mapping/fipnum.parquet` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- A grid model with a zone and region property

The grid model in RMS must contain a discrete zone and a region property which will
be used to assign `FIPNUM` values. The mappings between them will be automatically exported.

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.simulator_fipregions_mapping.create_fipnum_property
```

## Result

The table mapping from a unique `FIPNUM` value to corresponding region and zone names will
be exported to `share/results/tables/simulator_fipregions_mapping/fipnum.parquet`.


## Standard result schema

This standard result is made available with a validation schema that can be
used by consumers. A reference to the URL where this schema is located is
present within the `data.standard_result` key in its associated object
metadata.

| Field | Value |
| --- | --- |
| Version | {{ SimulatorFipregionsMappingSchema.VERSION }} |
| Filename | {{ SimulatorFipregionsMappingSchema.FILENAME }} |
| Path | {{ SimulatorFipregionsMappingSchema.PATH }} |
| Prod URL | {{ '[{}]({}) 🔒'.format(SimulatorFipregionsMappingSchema.prod_url(), SimulatorFipregionsMappingSchema.prod_url()) }}
| Dev URL | {{ '[{}]({}) 🔒'.format(SimulatorFipregionsMappingSchema.dev_url(), SimulatorFipregionsMappingSchema.dev_url()) }}

### Changelog

{{ SimulatorFipregionsMappingSchema.VERSION_CHANGELOG }}

### JSON schema

The current JSON schema is embedded here.

{{ SimulatorFipregionsMappingSchema.literalinclude }}
