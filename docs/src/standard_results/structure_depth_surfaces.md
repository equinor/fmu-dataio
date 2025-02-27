# Structure depth surfaces

This exports the modelled structural depth surfaces from within RMS.
These surfaces typically represent the final surface set generated during a structural
modelling workflow (after well conditioning), and frequently serve as the framework for
constructing the grid.

Note, it is only possible to export **one single set** of depth surface predictions per 
model workflow.

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/maps/structure_depth_surfaces/surfacename.gri` |
:::

## Requirements

- RMS
- depth surfaces stored in a horizon folder within RMS

The surfaces must be located within a horizon folder in RMS and be in domain `depth`.
This export function will automatically export all non-empty horizons from the provided folder.


## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.structure_depth_surfaces.export_structure_depth_surfaces
```

## Result

The surfaces from the horizon folder will be exported as 'irap_binary'
files to `share/results/maps/structure_depth_surfaces/surfacename.gri`.


## Standard result schema

This standard result is not presented in a tabular format; therefore, no validation
schema exists.
