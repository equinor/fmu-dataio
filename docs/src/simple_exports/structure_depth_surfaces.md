# Structure depth surfaces

This exports the modelled structural depth surfaces from within RMS. These
surfaces typically represent the final surface set generated during a
structural modelling workflow (after well conditioning), and frequently serve
as the framework for constructing the grid.

:::{note}
It is only possible to export **one single set** of depth surface predictions
per model workflow.
:::

:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/maps/structure_depth_surface/surfacename.gri` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- depth surfaces stored in a horizon folder within RMS

The surfaces must be located within a horizon folder in RMS and be in domain
`depth`. This export function will automatically export all non-empty
horizons from the provided folder.

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.structure_depth_surfaces.export_structure_depth_surfaces
```

## Result

The surfaces from the horizon folder will be exported as 'irap_binary' files
to `share/results/maps/structure_depth_surface/surfacename.gri`.

## Standard result schema

This standard result is not presented in a tabular format; therefore, no
validation schema exists.

## Load structure depth surfaces

Use the below loader function, loader object and interface to load and
interact with the exported structure depth surfaces standard results.

```{hint}
For more information about the purpose of these loader functions, see [Loading
Data](../overview.md#loading-data) in the [Overview](../overview.md).
```

### Usage

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.load_structure_depth_surfaces
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.StructureDepthSurfacesLoader
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.StructureDepthSurfacesLoader.list_realizations
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.StructureDepthSurfacesLoader.get_realization
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.StructureDepthSurfacesLoader.get_blobs
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.StructureDepthSurfacesLoader.save_realization
```
