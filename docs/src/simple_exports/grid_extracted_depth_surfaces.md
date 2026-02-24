# Extracted grid surfaces

This exports extracted grid surfaces from within RMS. These
surfaces are typically extracted from the geogrid (or any other grid) for QC 
purposes. Examples include ensuring that the grid maintains sufficient resolution
to honour zonation in the wells.

:::{note}
It is only possible to export **one single set** of extracted grid surfaces
per model workflow.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/maps/extracted_grid_depth_surface/surfacename.gri` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- extracted surfaces stored in a horizon folder within RMS

The extracted surfaces must be located within a horizon folder in RMS and be in domain
`depth`. This export function will automatically export all non-empty
horizons from the provided folder.

:::{tip}
Surfaces can be extracted from a grid by using the job `Extract Framework Data` from `Grid utilities`. 

For `Horizon output` the `Horizons` folder should be selected together with option `Map names to horizons`
to connect the grid zones with their corresponding horizon names.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.grid_extracted_depth_surfaces.export_grid_extracted_depth_surfaces
```

## Result

The surfaces from the horizon folder will be exported as 'irap_binary' files
to `share/results/maps/grid_extracted_depth_surface/surfacename.gri`.

## Standard result schema

This standard result is not presented in a tabular format; therefore, no
validation schema exists.