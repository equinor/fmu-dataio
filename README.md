# fmu-dataio
Utility functions for data transfer of FMU data with rich metadata, for REP, SUMO, WEBVIZ, etc.

These fmu.dataio can be ran both inside RMS and outside RMS.

For surfaces, grids, wells, polygons, the input object must be parsed by
xtgeo. For tables, the input is a pandas dataframe.

A configuration input is required and will within Equinor be read from the
so-called global_variables.yml produced by fmu-config. Details on syntax
will be given in the documentation.

As default, output with metadata will be stored in `../../share/results` for each
realization, while ensemble metadata when ran with ERT will be stored in
`/scratch/<field>/<user>/<case>/share/metadata`

## Usage

### Export a surface

```
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

```
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

### Initialise an case

This is typically done via a hook workflow in ERT. This will make it possible to
register a case for the Sumo uploader.


```
from fmu.config import utilities as ut
from fmu.dataio import ExportData

CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")


def initilize():

    exp = ExportData(config=CFG, flag=1)

    exp.case_metadata_to_file(rootfolder=<CASEDIR>)


## Installation

Install a spesific version (e.g. 0.1.1) directly from github through

```
pip install git+ssh://git@github.com/equinor/fmu-dataio@0.1.1
```

Local development and testing:

```
pip install -e .[tests,docs]
pytest
```
