# Simulator zone layer mapping


This reads zonation from a simulation grid in RMS and exports the corresponding
`layer / zone` mappings as the standard result `simulator_zone_layer_mapping`.

The layer index in the exported table is 1-based.

:::{note}
 Use the same grid model as the one used for flow simulation. Otherwise,
 layer mappings may not align with simulation results.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | **{{ SimulatorZoneLayerMappingSchema.VERSION }}** |
| Output | `share/results/tables/simulator_zone_layer_mapping/simulator_zone_layer_mapping.parquet` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- A grid model

The RMS grid model must be the same one used as basis for flow simulation.
The layer mappings are exported automatically.

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.simulator_zone_layer_mapping.export_simulator_zone_layer_mapping
```

## Result

A table mapping each unique `layer` index value (1-based) to its corresponding
zone name is exported to `share/results/tables/simulator_zone_layer_mapping/simulator_zone_layer_mapping.parquet`.


## Standard result schema

This standard result is made available with a validation schema that can be
used by consumers. A reference to the URL where this schema is located is
present within the `data.standard_result` key in its associated object
metadata.

| Field | Value |
| --- | --- |
| Version | {{ SimulatorZoneLayerMappingSchema.VERSION }} |
| Filename | {{ SimulatorZoneLayerMappingSchema.FILENAME }} |
| Path | {{ SimulatorZoneLayerMappingSchema.PATH }} |
| Prod URL | {{ '[{}]({}) 🔒'.format(SimulatorZoneLayerMappingSchema.prod_url(), SimulatorZoneLayerMappingSchema.prod_url()) }}
| Dev URL | {{ '[{}]({}) 🔒'.format(SimulatorZoneLayerMappingSchema.dev_url(), SimulatorZoneLayerMappingSchema.dev_url()) }}

### Changelog

{{ SimulatorZoneLayerMappingSchema.VERSION_CHANGELOG }}

### JSON schema

The current JSON schema is embedded here.

{{ SimulatorZoneLayerMappingSchema.literalinclude }}
