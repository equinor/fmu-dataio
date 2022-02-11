"""Test the production of aggregations metadata"""

# aggregations are single data objects representing a statistical aggregation across
# many data objects. Examples include:
# A surface representing the (point-wise) mean value across all
# predictions of that surface in an ensemble.

import shutil
import logging
from pathlib import Path, PurePath

import pytest

import numpy as np

import yaml
import json
import jsonschema

import xtgeo

import fmu.dataio
import fmu.dataio._export_item as ei

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CFG2 = {}

with open("tests/data/drogon/global_config2/global_variables.yml", "r") as stream:
    CFG2 = yaml.safe_load(stream)

CASEPATH = "tests/data/drogon/ertrun1"
TESTDIR = Path(__file__).parent.absolute()


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


def _parse_json(schema_path):
    """Parse the schema, return JSON"""
    with open(schema_path) as stream:
        data = json.load(stream)

    return data


def test_get_realization_ids():
    """Test the get_realization_ids method"""
    metas = [{"fmu": {"realization": {"id": x}}} for x in [0, 1, 3, 5]]

    dataio = fmu.dataio.ExportAggregatedData(source_metadata=metas)

    exp = fmu.dataio._export_item._ExportAggregatedItem(
        dataio=dataio,
        obj=None,
        operation=None,
        verbosity="DEBUG",
    )
    assert exp._get_realization_ids() == [0, 1, 3, 5]


def test_create_template():
    """Test the create_template private method"""

    # leaving this as a placeholder until we agree on the concepts.

    pass


def test_check_consistency(tmp_path):
    """Test the check_consistency private method"""

    # all surface shall be from the same case/iteration?

    # all surfaces shall be from different realizations?

    # all surfaces shall have same relative file path?

    # all surfaces shall have same data.name?

    # make realizations
    export_paths, _, _ = _create_realization_surfaces(tmp_path)

    # read the generated realization metadatas
    metadatas = [_open_metadata(export_path) for export_path in export_paths]

    # make a fake surface to use further in these tests
    obj = xtgeo.RegularSurface(
        name="SomeAggregatedSurface", ncol=3, nrow=4, xinc=22, yinc=22, values=0
    )

    # verify that they are consistent out of the box
    dataio = fmu.dataio.ExportAggregatedData(
        source_metadata=metadatas,  # list of metadata for the surfaces used
        aggregation_id="0000-0000-00000",
        verbosity="DEBUG",
    )
    exportitem = ei._ExportAggregatedItem(dataio, obj, "mean", verbosity="DEBUG")
    exportitem._check_consistency()

    # assert failure when case name is not the same
    _original = metadatas[0]["fmu"]["case"]["name"]
    metadatas[0]["fmu"]["case"]["name"] = "different case name"
    with pytest.raises(ValueError) as e_info:
        exportitem._check_consistency()
    assert "fmu.case.name" in str(e_info)
    metadatas[0]["fmu"]["case"]["name"] = _original

    # assert failure when case uuid is not the same
    _original = metadatas[0]["fmu"]["case"]["uuid"]
    metadatas[0]["fmu"]["case"]["uuid"] = "a different uuid"
    with pytest.raises(ValueError) as e_info:
        exportitem._check_consistency()
    assert "fmu.case.uuid" in str(e_info)
    metadatas[0]["fmu"]["case"]["uuid"] = _original

    # assert failure when masterdata is not the same
    # also testing when value is a dict
    _original = metadatas[0]["masterdata"]
    metadatas[0]["masterdata"] = {"not": "right"}
    with pytest.raises(ValueError) as e_info:
        exportitem._check_consistency()
    assert "masterdata" in str(e_info)
    metadatas[0]["masterdata"] = _original

    # assert failure when version is not the same
    _original = metadatas[0]["version"]
    metadatas[0]["version"] = {"not": "right"}
    with pytest.raises(ValueError) as e_info:
        exportitem._check_consistency()
    assert "version" in str(e_info)
    metadatas[0]["version"] = _original

    # assert failure when data.vertical_domain is not the same
    _original = metadatas[0]["data"]["vertical_domain"]
    metadatas[0]["data"]["vertical_domain"] = 12345.0
    with pytest.raises(ValueError) as e_info:
        exportitem._check_consistency()
    assert "data.vertical_domain" in str(e_info)
    metadatas[0]["data"]["vertical_domain"] = _original

    # assert failure when content is not the same
    _original = metadatas[0]["data"]["content"]
    metadatas[0]["data"]["content"] = "a different content"
    with pytest.raises(ValueError) as e_info:
        exportitem._check_consistency()
    assert "data.content" in str(e_info)

    # ... + assert warning only when explicitly set
    exportitem.raise_on_inconsistency = False
    with pytest.warns(UserWarning, match="data.content"):
        exportitem._check_consistency()
    metadatas[0]["data"]["content"] = _original


def test_generate_metadata_instance(tmp_path):
    """Test the generate_metadata public method.

    In this test, pretend to be an aggregation service which is using fmu-dataio only
    for creating metadata. In this context, the service will never materialize a file
    to the disk. All communication will be across REST API.
    """

    # Dummy: make some realizations
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
        aggregation_id="0000-0000-00000",
        verbosity="DEBUG",
    )
    meta = exp.generate_metadata(meansurf, operation="mean", verbosity="DEBUG")
    # ...possible alternative/addition to an export function, e.g. exp.export(meansurf)
    # as the use cases most likely will want to retain the result in memory and send
    # it to an API rather than write to disk. If service wants to write to disk, it can
    # dump it afterwards or we can add an .export method.

    # at this point, the aggregation service will send the results somewhere else, e.g.
    # Sumo or similar.

    # verify the results
    assert "realization" not in meta["fmu"]
    assert "aggregation" in meta["fmu"]

    aggmeta = meta["fmu"]["aggregation"]
    assert aggmeta["operation"] == "mean"
    assert aggmeta["realization_ids"] == realizations
    assert "id" in aggmeta

    assert meta["class"] == "surface"

    assert "access" in meta

    assert "file" in meta
    assert "relative_path" in meta["file"]
    _frp = meta["file"]["relative_path"]
    assert _frp.startswith("iter-0/share/results"), _frp
    assert _frp.endswith("--mean.gri"), _frp

    # validation against schema
    schema = _parse_json(
        str(PurePath(TESTDIR, "../schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    jsonschema.validate(instance=meta, schema=schema)


def test_generate_metadata_export_files(tmp_path):
    """Test the export public method.

    In this test, pretend to be an aggregation service which is using fmu-dataio both
    for creating metadata and for exporting to disk.
    """

    # Dummy: make some realizations
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
        aggregation_id="0000-0000-00000",  # aggregation service holds the element.id
        verbosity="DEBUG",
    )
    outpath = tmp_path
    savedpath = exp.export(
        meansurf, operation="mean", casepath=outpath, verbosity="DEBUG"
    )

    sharepath = "iter-0/share/results/maps/"
    outfile = Path(outpath) / sharepath / "constantvalueis0--what_descr--mean.gri"
    assert savedpath == outfile, (str(savedpath), str(outfile))
    assert outfile.exists()

    outmetafile = (
        Path(outpath) / sharepath / ".constantvalueis0--what_descr--mean.gri.yml"
    )

    with open(outmetafile, "r") as stream:
        meta = yaml.safe_load(stream)

    assert "realization" not in meta["fmu"]
    assert "aggregation" in meta["fmu"]

    assert meta["fmu"]["aggregation"]["operation"] == "mean"
    assert meta["fmu"]["aggregation"]["realization_ids"] == realizations
    assert meta["class"] == "surface"

    assert "access" in meta

    assert "file" in meta
    assert meta["file"]["relative_path"].startswith("iter-0/share/results"), meta[
        "file"
    ]["relative_path"]

    # validation against schema
    schema = _parse_json(
        str(PurePath(TESTDIR, "../schema/definitions/0.8.0/schema/fmu_results.json"))
    )
    jsonschema.validate(instance=meta, schema=schema)
