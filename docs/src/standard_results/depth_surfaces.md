# Modelled depth prediction surfaces

This exports the modelled depth prediction surfaces from within RMS.
These surfaces typically represent the final surface set generated during a structural
modeling workflow (after well conditioning), and serve as the framework for constructing the grid.

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/maps/depth_predictions/surfacename.gri` |
:::

## Requirements

- RMS
- depth surfaces stored in a horizon folder within RMS

The depth surfaces should be located within a horizon folder in RMS.
The simplified export function will use the RMS API behind the scene to automatically
identify non-empty horizons from the folder, and export them using `fmu.dataio`.


## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.depth_prediction_surfaces.export_depth_prediction_surfaces
```

## Result

The surfaces from within the horizon folder will be exported as 'irap_binary'
files to `share/results/maps/depth_predictions/surfacename.gri`.


## Standard result schema

This standard result is not presented in a tabular format; therefore, no validation
schema exists.


