# fmu-dataio

Utility functions for data transfer of FMU data with rich metadata, for REP,
SUMO, WEBVIZ, etc.

These fmu.dataio functions can be ran both inside RMS and outside RMS with
exactly the same syntax.

For surfaces, grids, wells, polygons, the input object must be parsed by
xtgeo. Tables must be represented as a pandas dataframe.

A configuration input is required and will within Equinor be read from the
so-called `global_variables.yml` produced by fmu-config. Details on syntax
will be given in the documentation.

As default, output with metadata will be stored in `../../share/results` for each
realization, while ensemble metadata when run with ERT will be stored in
`/scratch/<field>/<user>/<case>/share/metadata`

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

    mycase.to_file(rootfolder=CDIR, casename=CNAME, caseuser=CUSER, description=DSC)

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
        tagname="Some Descr",
        verbosity="WARNING",
    )

    exp.to_file(srf)

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
        tagname="voltable",
    )

    exp.to_file(vol)

if __name__ == "__main__":
    export_some_table()

```


## Installation

Install a specific version (e.g. 0.1.1) directly from github through

```console
pip install git+ssh://git@github.com/equinor/fmu-dataio@0.1.1
```

Local development and testing:

```console
pip install -e .[tests,docs]
pytest
```

## License

Apache 2.0
