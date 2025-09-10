# Structure time surfaces

This exports the modelled structural time surfaces from within RMS. These
surfaces serve as the input for depth conversion in RMS and form the basis for
generating the structural framework in depth. Typically, they are extracted
from a structural model in time domain.

:::{note}
It is only possible to export **one single set** of time surface predictions
per model workflow.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/maps/structure_time_surface/surfacename.gri` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- time surfaces stored in a horizon folder within RMS

The surfaces must be located within a horizon folder in RMS and be in domain
`time`. This export function will automatically export all non-empty horizons
from the provided folder.

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.structure_time_surfaces.export_structure_time_surfaces
```

## Result

The surfaces from the horizon folder will be exported as 'irap_binary' files
to `share/results/maps/structure_time_surface/surfacename.gri`.

## Standard result schema

This standard result is not presented in a tabular format; therefore, no
validation schema exists.
