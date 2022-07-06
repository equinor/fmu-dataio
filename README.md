# fmu-dataio

![linting](https://github.com/equinor/fmu-dataio/workflows/linting/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![PyPI version](https://badge.fury.io/py/fmu-dataio.svg)](https://badge.fury.io/py/fmu-dataio)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fmu-dataio.svg)
![PyPI - License](https://img.shields.io/pypi/l/fmu-dataio.svg)

Utility functions for data transfer of FMU data with rich metadata, for REP,
SUMO, WEBVIZ, etc.

These fmu.dataio functions can be ran both inside RMS and outside RMS with
exactly the same syntax.

For surfaces, grids, wells, polygons, the input object must be parsed by
xtgeo. Tables must be represented as a pandas dataframe or pyarrow.

A configuration input is required and will within Equinor be read from the
so-called `global_variables.yml` produced by fmu-config. Details on syntax
will be given in the documentation.

As default, output with metadata will be stored in `share/results` for each
realization, while ensemble metadata when run with ERT will be stored in
`/scratch/<field>/<user>/<case>/share/metadata`

# Metadata definitions
![](https://api.radix.equinor.com/api/v1/applications/fmu-schemas/environments/dev/buildstatus)

Definitions of metadata applied to FMU results are in the form of a [JSON schema](https://json-schema.org/).
Within Equinor, the schema is available on a Radix-hosted endpoint.

## Usage

### Initialise a case

This is typically done via a hook workflow in ERT. This will make it possible to
register a case for the Sumo uploader. As default, this will give a case metadata
file stored in `/scratch/somefield/someuser/somecase/share/metadata/fmu_case.yml`.


```python
from fmu.config import utilities as ut
from fmu.dataio import InitializeCase

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

CDIR = "/scratch/somefield"
CNAME = "somecase"
CUSER = "someuser"
DSC = "The ultimate history match"

def initalize():

    mycase = InitializeCase(config=CFG)

    mycase.export(rootfolder=CDIR, casename=CNAME, caseuser=CUSER, description=DSC)

```

### Export a surface

```python
import xtgeo
from fmu.config import utilities as ut
from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")


def export_some_surface():
    srf = xtgeo.surface_from_file("top_of_some.gri")

    exp = ExportData(
        config=CFG,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        verbosity="WARNING",
    )

    exp.export(srf, tagname="Some Descr")

if __name__ == "__main__":
    export_some_surface()

```


### Export a table

This is coming functionality and code in example is tentative!

```python
import pandas as pd
from fmu.config import utilities as ut
from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")


def export_some_table():
    vol = pd.read_csv("some_table_vol.csv")

    exp = ExportData(
        config=CFG,
        content="volumetrics",
        unit="m",
        is_prediction=True,
        is_observation=False,
    )

    exp.export(vol, tagname="voltable")

if __name__ == "__main__":
    export_some_table()

```


## Installation

Install a specific version (e.g. 0.1.1) directly from github through:

```console
pip install git+ssh://git@github.com/equinor/fmu-dataio@0.1.1
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

## License

Apache 2.0
