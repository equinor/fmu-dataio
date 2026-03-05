# Grid model static

This exports a static grid model with standard properties from within RMS. 

The following properties must be provided:

- `zones` - Classification of geological zonations within the reservoir.
- `regions` - Classification of distinct geographic regions.
- `porosity` - The fraction of the cell volume that is pore space.
- `permeability` - The measure of how easily fluids flow horizontally.
- `saturation_water` - The fraction of the pore space occupied by water.

The following properties can optionally be included:

- `facies` - Classification of rock types influencing reservoir properties.
- `net_to_gross` - Classification of net-to-gross ratio within the reservoir.
- `permeability_vertical` - The measure of how easily fluids flow in the vertical direction.
- `volume_shale` - The fraction of the cell volume that is shale.

In addition to the properties that must be provided as input, the following properties will be
picked up and need to exist in the grid model with the correct name. These properties can easily
be output from the RMS volumetrics job.
- `bulk_volume_oil` - The bulk volume of oil in the cell. Must be named `Oil_bulk`.
- `bulk_volume_gas` - The bulk volume of gas in the cell. Must be named `Gas_bulk`.
- `fluid_indicator` - Classification of different fluids (oil/gas/water) within the reservoir. Must be named `Discrete_fluid`.

:::{note}
It is possible to omit one of `bulk_volume_oil` or `bulk_volume_gas` if that fluid is
not present in the field.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/grids/grid_model_static/gridname.roff` and `gridname--propertyname.roff`|
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- grid model in RMS containing standard properties
- bulk volume fluid properties with names `Oil_bulk` and `Gas_bulk` (one or both)
- fluid indicator property with name `Discrete_fluid` 

The grid model needs to be located in RMS and contain standard properties.
This export function will validate that the properties are of expected type and
have values within expected ranges e.g. a `porosity` property must have values
between 0 and 1.

:::{tip}
The easiest way to produce the  `bulk_volume_oil` or `bulk_volume_gas` properties is to
enable `Parameter` output from `Bulk` in the volumetrics job in RMS. The `Discrete_fluid`
property can be output from the same job by enabling the `Create discrete fluid parameter`.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.grid_model_static.export_grid_model_static
```

## Result

The grid and it's properties will be exported as separate files of type 'roff'
to `share/results/maps/grid_model_static/gridname.roff` and `gridname--propertyname.roff`.

## Standard result schema

This standard result is not presented in a tabular format; therefore, no
validation schema exists.
