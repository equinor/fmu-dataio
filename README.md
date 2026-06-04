# fmu-dataio

[![Test](https://github.com/equinor/fmu-dataio/actions/workflows/ci-fmudataio.yml/badge.svg)](https://github.com/equinor/fmu-dataio/actions/workflows/ci-fmudataio.yml)
[![PyPI version](https://badge.fury.io/py/fmu-dataio.svg)](https://badge.fury.io/py/fmu-dataio)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fmu-dataio.svg)
![PyPI - License](https://img.shields.io/pypi/l/fmu-dataio.svg)
![ReadTheDocs](https://readthedocs.org/projects/fmu-dataio/badge/?version=latest&style=flat)

---

**Documentation**: <a href="https://fmu-dataio.readthedocs.io/en/latest/" target="_blank">https://fmu-dataio.readthedocs.io/en/latest/</a>

**Source Code**: <a href="https://github.com/equinor/fmu-dataio/" target="_blank">https://github.com/equinor/fmu-dataio/</a>

---

**fmu-dataio** is a library for handling data flow in and out of Fast Model
Update workflows.  For export, it automates the adherence to the FMU data
standard ✅ including both file and folder conventions as well as richer
metadata 🔖 for use by various data consumers both inside and outside the
FMU context via Sumo.

**fmu-dataio** is designed to be used with the same syntax in all parts of an
FMU workflow, including post- and pre-processing jobs and as part of
[Ert](https://github.com/equinor/ert) `FORWARD_MODEL`, both inside and outside
RMS.

**fmu-dataio** is also showcased in
[Drogon](https://github.com/equinor/fmu-drogon). 💪

## Data standard definitions

The metadata standard is defined by [JSON schemas](https://json-schema.org/). Within Equinor,
the schema is available on a Radix-hosted endpoint ⚡

- Radix Dev: ![Radix Dev](https://api.radix.equinor.com/api/v1/applications/fmu-schemas/environments/dev/buildstatus)

## Updating schemas

Check out the [Updating
schemas](https://fmu-dataio.readthedocs.io/en/latest/update_schemas.html)
page in the documentation for instructions.

## License

This project is licensed under the terms of the [Apache 2.0](https://github.com/equinor/fmu-dataio/LICENSE) license.

## Note on RMS Roxar API Integration

![RMS License Required](https://img.shields.io/badge/RMS-License%20Required-important)

The following statement applies to all functionalities in fmu-dataio that
integrates with the RMS APIs:

> RMS is neither open source nor a free software. Use of RMS requires a valid
> software license agreement.
