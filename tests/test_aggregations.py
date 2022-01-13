"""Test the production of aggregations metadata"""

# aggregations are single data objects representing a statistical aggregation across
# many data objects. Examples include:
# A surface representing the (point-wise) mean value across all
# predictions of that surface in an ensemble.

import shutil
import logging
from pathlib import Path

import numpy as np

import yaml
import xtgeo

import fmu.dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CFG2 = {}
with open("tests/data/drogon/global_config2/global_variables.yml", "r") as stream:
    CFG2 = yaml.safe_load(stream)

CASEPATH = "tests/data/drogon/ertrun1"


def _create_realization_surfaces(tmp_path):
    """Create individual realization surfaces to be used for testing aggregations"""

    # make it look like an ERT run
    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")

    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    constant_values = [0, 10]
    realizations = [0, 1]

    export_paths = []

    # produce surfaces with known value, export with dataio
    for constant_value, real in zip(constant_values, realizations):

        # make it look like an ERT run
        runfolder = (
            current / "mycase" / f"realization-{real}" / "iter-0" / "rms" / "model"
        )
        runfolder.mkdir(parents=True, exist_ok=True)
        out = (
            current
            / "mycase"
            / f"realization-{real}"
            / "iter-0"
            / "share"
            / "results"
            / "maps"
        )

        # fake the export of a single realization surface
        exp = fmu.dataio.ExportData(
            config=CFG2,
            content="depth",
            unit="m",
            vertical_domain={"depth": "msl"},
            timedata=None,
            is_prediction=True,
            is_observation=False,
            tagname="what Descr",
            verbosity="INFO",
            runfolder=runfolder.resolve(),
            workflow="my current workflow",
            inside_rms=True,
        )

        # make a surface
        _surf = xtgeo.RegularSurface(
            name=f"ConstantValueIs{constant_value}",
            ncol=10,
            nrow=10,
            xinc=1,
            yinc=1,
            values=constant_value,
        )

        # export the surface
        export_paths.append(exp.to_file(_surf))

    return export_paths, realizations, constant_values


def _open_metadata(path):
    metadata_path = f"{Path(path).parent}/.{Path(path).name}.yml"
    with open(metadata_path, "r") as stream:
        data = yaml.safe_load(stream)
    return data


def test_get_realization_ids():
    """Test the get_realization_ids method"""
    metas = [{"fmu": {"realization": {"id": x}}} for x in [0, 1, 3, 5]]
    exp = fmu.dataio.ExportAggregatedData(source_metadata=metas, element_id=0)
    assert exp._get_realization_ids() == [0, 1, 3, 5]


def test_check_consistency():
    """Test the check_consistency method"""

    # all surface shall be from the same case/iteration?

    # all surfaces shall be from different realizations?

    # all surfaces shall have same relative file path?

    # all surfaces shall have same data.name?

    pass


def test_generate_metadata(tmp_path):
    """Test the generate metadata method"""

    # make realizations
    export_paths, realizations, constant_values = _create_realization_surfaces(tmp_path)

    # Pretend to be an aggregation service which has collected a set of surfaces with
    # corresponding metadata compliant with fmu-dataio.
    surfaces = xtgeo.Surfaces(export_paths)
    metadatas = [_open_metadata(export_path) for export_path in export_paths]

    # verify assumptions
    assert (
        len(surfaces.surfaces)
        == len(metadatas)
        == len(realizations)
        == len(constant_values)
    )

    # pretend to be aggregation service, and create an aggregation
    meansurf = surfaces.apply(np.nanmean, axis=0)

    # pretend to be aggregation service generating metadata for an aggregation
    exp = fmu.dataio.ExportAggregatedData(
        source_metadata=metadatas,  # list of metadata for the surfaces used
        element_id="0000-0000-00000",
    )
    meta = exp.generate_metadata(meansurf, operation="mean")
    # ...possible alternative/addition to an export function, e.g. exp.export(meansurf)
    # as the use cases most likely will want to retain the result in memory and send
    # it to an API rather than write to disk. If service wants to write to disk, it can
    # dump it afterwards or we can add an .export method.

    # verify the results
    assert "realization" not in meta["data"]
    assert "aggregation" in meta["data"]
    aggmeta = meta["data"]["aggregation"]
    assert aggmeta["operation"] == "mean"
    assert aggmeta["realization_ids"] == realizations

    # validation against schema
