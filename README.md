# fmu-dataio

![linting](https://github.com/equinor/fmu-dataio/workflows/linting/badge.svg)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI version](https://badge.fury.io/py/fmu-dataio.svg)](https://badge.fury.io/py/fmu-dataio)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fmu-dataio.svg)
![PyPI - License](https://img.shields.io/pypi/l/fmu-dataio.svg)
![ReadTheDocs](https://readthedocs.org/projects/fmu-dataio/badge/?version=latest&style=flat)

**fmu-dataio** is a library for handling data flow in and out of Fast Model Update workflows.
For export, it automates the adherence to the FMU data standard ✅ including both file and folder
conventions as well as richer metadata 🔖 for use by various data consumers both inside and
outside the FMU context via Sumo.

**fmu-dataio** is designed to be used with the same syntax in all parts of an FMU workflow, 
including post- and pre-processing jobs and as part of ERT `FORWARD_MODEL`, both inside and outside RMS.

👉 [Detailed documentation for fmu-dataio at Read the Docs.](https://fmu-dataio.readthedocs.io/en/latest/) 👀

**fmu-dataio** is also showcased in Drogon. 💪

## Data standard definitions
![Radix](https://api.radix.equinor.com/api/v1/applications/fmu-schemas/environments/dev/buildstatus)

The metadata standard is defined by a [JSON schema](https://json-schema.org/). Within Equinor,
the schema is available on a Radix-hosted endpoint ⚡
