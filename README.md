# fmu-dataio

![linting](https://github.com/equinor/fmu-dataio/workflows/linting/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
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


## Installation

Install a specific version (e.g. 1.2.3) directly from github through:

```console
pip install git+ssh://git@github.com/equinor/fmu-dataio@1.2.3
```

Local development and testing:

Make your own fork of fmu-dataio and then clone it locally on unix.
Create a virtual environment:
```console
python -m venv my_venv
```
Activate the venv: 
```console
source my_venv/bin/activate
```
Upgrade pip and install fmu-dataio from the source:
```console
pip install --upgrade pip
pip install -e .
```
Install requirements for running tests:
```console
pip install -e .[tests,docs]
```
Then run the command: 
```console
pytest
```

