# Initial fluid contact surfaces

This exports modelled initial fluid contact surfaces from within RMS.

Each fluid contact surface corresponds to a specific zone or a group of zones
that share a common fluid contact. These surfaces typically cover the full
spatial extent of the zone, and are not restricted to areas above the contact.

The fluid contact types supported is
- `fwl` (Free water level)
- `fgl` (Free gas level)
- `goc` (Gas-oil contact)
- `gwc` (Gas-water contact)
- `owc` (Oil-water contact)


:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version | NA |
| Output | `share/results/maps/fluid_contact_surface/contactname/surfacename.gri` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- fluid contact surfaces stored in the `General 2D data` folder within RMS.
- names of surfaces defined in the `stratigraphy` block

A folder named `fluid_contact_surfaces` must exist in the root of the `General
2D data` folder in RMS. This folder should contain at least one subfolder with
a valid fluid contact name (e.g., `fwl`, see the list above). The export
function will automatically process and export all surfaces found within these
subfolders.

:::{note}
The names of the fluid contact surfaces must be defined in the `stratigraphy`
block of the configuration to enable mapping against masterdata.
:::

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.fluid_contact_surfaces.export_fluid_contact_surfaces
```

## Result

The fluid contact surfaces from the `General 2D data` folder will be exported
as 'irap_binary' files to
`share/results/maps/fluid_contact_surface/contactname/surfacename.gri`.

## Standard result schema

This standard result is not presented in a tabular format; therefore, no
validation schema exists.

## Load fluid contact surfaces

Use the below loader function, loader object and interface to load and
interact with the exported fluid contact surfaces standard results.

```{hint}
For more information about the purpose of these loader functions, see [Loading
Data](../overview.md#loading-data) in the [Overview](../overview.md).
```

### Usage

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.load_fluid_contact_surfaces
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FluidContactSurfacesLoader
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FluidContactSurfacesLoader.list_realizations
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FluidContactSurfacesLoader.get_realization
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FluidContactSurfacesLoader.get_blobs
```

```{eval-rst}
.. autofunction:: fmu.dataio.load.load_standard_results.FluidContactSurfacesLoader.save_realization
```
