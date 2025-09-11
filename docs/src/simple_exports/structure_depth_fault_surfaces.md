# Structure depth fault surfaces

This exports the modelled structure depth fault surfaces from within
RMS. For each fault surface in a structural model, nodes and triangles are
retrieved from RMS and exported as triangulated surfaces in the TSurf file
format used in for example the GOCAD software.


:::{table} Current
:widths: auto
:align: left

| Field | Value |
| --- | --- |
| Version |  NA |
| Output | `share/results/maps/structure_depth_fault_surface/faultname.ts` |
| Security classification | 🟡 Internal |
:::

## Requirements

- RMS
- structural model with set of fault surfaces

The export function will automatically export all fault surfaces in
the selected structural model.

## Usage

```{eval-rst}
.. autofunction:: fmu.dataio.export.rms.structure_depth_fault_surfaces.export_structure_depth_fault_surfaces
```

## Result

Given a fault surface in the structural model named `F1`, the result file
will be `share/results/maps/structure_depth_fault_surface/f1.ts`.

The `.ts` file extension indicates that the file represents the fault surface
in the TSurf file format.

The file content has been validated using a Pydantic model representing
TSurf data.

## Standard result schema

This standard result is not presented in a tabular format; therefore, no
validation schema exists.

## Load structure depth fault surfaces

The loader interface for structure depth fault surfaces standard results
is still under development and not supported yet.
