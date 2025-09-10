# Structure depth isochores

This exports the modelled structural depth isochores from within RMS. These
isochores are surfaces that represents the true vertical thickness of each
stratigraphic zone (unit) from the final structural model in depth.

:::{note}
It is only possible to export **one single set** of depth isochore predictions
per model workflow, i.e. one surface object per stratigraphic zone.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/maps/structure_depth_isochore/zonename.gri` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- thickness surfaces stored in a zone folder within RMS

The surfaces must be located within a zone folder in RMS. This export function
will automatically export all non-empty zones from the provided folder.

:::{important}
These surfaces should be extracted from the final depth horizon model using
the `Extract Horizon/Zone Data` job in RMS. This will ensure that the surfaces
are a true representation of the thickness of a zone in the model, e.g if
there is an erosional surface, this is correctly reflected.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.structure_depth_isochores.export_structure_depth_isochores
```

## Result

The surfaces from the horizon folder will be exported as 'irap_binary' files
to `share/results/maps/structure_depth_isochore/zonename.gri`.

## Standard result schema

This standard result is not presented in a tabular format; therefore, no
validation schema exists.

## Load structure depth isochores

The loader interface for structure depth isochores standard results is still
under development and not supported yet.
