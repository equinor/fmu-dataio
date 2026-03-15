# Grid model static

This exports a static grid model with standard properties from within RMS. 

The following properties will be included in the exported grid model:

- `zonation` 
- `regions` 
- `porosity`
- `permeability`
- `saturation_water` 
- `fluid_indicator`
- `bulk_volume_oil` and/or `bulk_volume_gas`

The following properties can optionally be included:

- `facies` 
- `net_to_gross` 
- `permeability_vertical` 
- `volume_shale` 


:::{note}
It is possible to omit one of `bulk_volume_oil` or `bulk_volume_gas` if that fluid is not present
in the field.
:::

:::{admonition} Property descriptions
:class: dropdown

```{eval-rst}
.. autoclass:: fmu.datamodels.fmu_results.enums.PropertyAttribute
    :members: zonation, regions, porosity, permeability, saturation_water, bulk_volume_oil, bulk_volume_gas, fluid_indicator, facies, net_to_gross, permeability_vertical, volume_shale
    :exclude-members: __new__, __init__
    :no-index:
```
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/grids/grid_model_static/gridname.roff`<br>`share/results/grids/grid_model_static/gridname--propertyname.roff` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- grid model in RMS containing standard properties
- bulk volume fluid properties with names `Oil_bulk` and/or `Gas_bulk` (as applicable)
- fluid indicator property with name `Discrete_fluid` 

The grid model needs to be located in RMS and contain standard properties.

For most properties, the RMS property name is provided as function input.
The `bulk_volume_oil`, `bulk_volume_gas`, and `fluid_indicator` properties are however
detected automatically and must exist in the grid with these exact RMS names:
`Oil_bulk`, `Gas_bulk` and `Discrete_fluid`.

This export function will validate that the properties are of expected type and
have values within expected ranges e.g. a `porosity` property must have values
between 0 and 1.

:::{tip}
The easiest way to produce the `bulk_volume_oil` or `bulk_volume_gas` properties is to
enable `Parameter` output from `Bulk` in the volumetrics job in RMS. The `Discrete_fluid`
property can be output from the same job by enabling the `Create discrete fluid parameter`.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.grid_model_static.export_grid_model_static
```

## Result

The grid and its properties will be exported as separate files of type 'roff'
to `share/results/grids/grid_model_static/gridname.roff` and `gridname--propertyname.roff`.

## Standard result schema

This standard result is not presented in a tabular format; therefore, no
validation schema exists.
