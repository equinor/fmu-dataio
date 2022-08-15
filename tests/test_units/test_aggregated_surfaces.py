"""Test the dataio running with aggregated surface."""
import logging
import os

import pytest
import xtgeo

import fmu.dataio._utils as utils
import fmu.dataio.dataio as dataio

logger = logging.getLogger(__name__)


def test_regsurf_aggregated(fmurun_w_casemetadata, aggr_surfs_mean):
    """Test generating aggragated metadata for a surface, where input has metadata."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    aggr_mean, metas = aggr_surfs_mean  # xtgeo_object, list-of-metadata-dicts
    logger.info("Aggr. mean is %s", aggr_mean.values.mean())

    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd",
        verbosity="INFO",
        aggregation_id="1234",
    )
    newmeta = aggdata.generate_metadata(aggr_mean)
    logger.debug("New metadata:\n%s", utils.prettyprint_dict(newmeta))
    assert newmeta["fmu"]["aggregation"]["id"] == "1234"


def test_regsurf_aggregated_export(fmurun_w_casemetadata, aggr_surfs_mean):
    """Test generating aggragated metadata, now with export method.

    Here the input metadata have both absolute and relative paths stored in the
    metadata, which are the basis for generating the paths to the aggregated data,
    """
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    aggr_mean, metas = aggr_surfs_mean  # xtgeo_object, list-of-metadata-dicts
    logger.info("Aggr. mean is %s", aggr_mean.values.mean())

    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd",
        tagname="mean",
        verbosity="INFO",
        aggregation_id="1234",
    )

    mypath = aggdata.export(aggr_mean)

    logger.info("Relative path: %s", aggdata._metadata["file"]["relative_path"])
    logger.info("Absolute path: %s", aggdata._metadata["file"]["absolute_path"])
    logger.debug(
        "Final metadata after export:\n%s", utils.prettyprint_dict(aggdata._metadata)
    )

    assert "iter-0/share/results/maps/myaggrd--mean.gri" in mypath


def test_regsurf_aggregated_alt_keys(fmurun_w_casemetadata, aggr_surfs_mean):
    """Test generating aggragated metadata, putting keys in export instead."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    aggr_mean, metas = aggr_surfs_mean  # xtgeo_object, list-of-metadata-dicts
    logger.info("Aggr. mean is %s", aggr_mean.values.mean())

    aggdata1 = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd",
        tagname="mean",
        verbosity="INFO",
        aggregation_id="1234",
    )

    meta1 = aggdata1.generate_metadata(aggr_mean)

    # alternative
    aggdata2 = dataio.AggregatedData()

    meta2 = aggdata2.generate_metadata(
        aggr_mean,
        source_metadata=metas,
        operation="mean",
        name="myaggrd",
        tagname="mean",
        verbosity="INFO",
        aggregation_id="1234",
    )

    # alternative with export
    aggdata3 = dataio.AggregatedData()

    _ = aggdata3.export(
        aggr_mean,
        source_metadata=metas,
        operation="mean",
        name="myaggrd",
        tagname="mean",
        verbosity="INFO",
        aggregation_id="1234",
    )
    meta3 = aggdata3._metadata

    del meta1["tracklog"]
    del meta2["tracklog"]
    del meta3["tracklog"]

    assert meta1 == meta2 == meta3


def test_regsurf_aggr_export_give_casepath(fmurun_w_casemetadata, aggr_surfs_mean):
    """Test generating aggragated metadata, with export method but explicit casepath.

    Here the input metadata have both absolute and relative paths stored in the
    metadata, which are the basis for generating the paths to the aggregated data,
    but here a user given casepath will override. This casepath must exist in advance!
    """
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)
    casepath = fmurun_w_casemetadata.parent.parent.parent / "customcase"
    casepath.mkdir(parents=True, exist_ok=True)

    aggr_mean, metas = aggr_surfs_mean  # xtgeo_object, list-of-metadata-dicts
    logger.info("Aggr. mean is %s", aggr_mean.values.mean())

    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        casepath=casepath,
        operation="mean",
        name="myaggrd",
        tagname="mean",
        verbosity="INFO",
        aggregation_id="1234abcd",
    )

    mypath = aggdata.export(aggr_mean)

    logger.debug(
        "Final metadata after export:\n%s", utils.prettyprint_dict(aggdata._metadata)
    )

    assert "customcase/iter-0/share/results/maps/myaggrd--mean.gri" in mypath


def test_regsurf_aggr_export_give_casepath_noex(fmurun_w_casemetadata, aggr_surfs_mean):
    """Test generating aggragated metadata, with export method but nonexisting casepath.

    This should raise a ValueError
    """
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)
    casepath = fmurun_w_casemetadata.parent.parent.parent / "customcase2"
    # ... but do not create it

    aggr_mean, metas = aggr_surfs_mean  # xtgeo_object, list-of-metadata-dicts

    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        casepath=casepath,
        operation="mean",
        name="myaggrd",
        tagname="mean",
        verbosity="INFO",
        aggregation_id="1234abcd",
    )

    with pytest.raises(ValueError):
        _ = aggdata.export(aggr_mean)


def test_regsurf_aggr_export_abspath_none(fmurun_w_casemetadata, aggr_surfs_mean):
    """Test generating aggragated metadata, but the abspath input is None.

    This should give None as abspath also for the result
    """
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    aggr_mean, metas = aggr_surfs_mean  # xtgeo_object, list-of-metadata-dicts

    # manipulate first metadata record so mimic abspath is None
    metas[0]["file"]["absolute_path"] = None

    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd",
        tagname="mean",
        verbosity="INFO",
        aggregation_id="1234abcd",
    )

    newmeta = aggdata.generate_metadata(aggr_mean)
    logger.debug("Final metadata after export:\n%s", utils.prettyprint_dict(newmeta))

    # now export should raise an Error since abspath is None (and casepath is not given)
    with pytest.raises(IOError):
        _ = aggdata.export(aggr_mean)


def test_regsurf_aggregated_aggregation_id(fmurun_w_casemetadata, aggr_surfs_mean):
    """Test generating aggragated metadata, tests on aggrd id"""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    aggr_mean, metas = aggr_surfs_mean  # xtgeo_object, list-of-metadata-dicts
    logger.info("Aggr. mean is %s", aggr_mean.values.mean())  # shall be 1238.5

    # let missing aggregation_id argument generate the id
    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd2",
        verbosity="INFO",
    )
    newmeta = aggdata.generate_metadata(aggr_mean)
    logger.debug("New metadata:\n%s", utils.prettyprint_dict(newmeta))
    assert newmeta["fmu"]["aggregation"]["id"] != "1234"  # shall be uuid

    # let aggregation input None generate the id
    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd2",
        verbosity="INFO",
        aggregation_id=None,
    )
    newmeta = aggdata.generate_metadata(aggr_mean)
    logger.debug("New metadata:\n%s", utils.prettyprint_dict(newmeta))
    assert "id" in newmeta["fmu"]["aggregation"]
    assert newmeta["fmu"]["aggregation"]["id"] != "1234"  # shall be uuid

    # let aggregation_id argument be used as aggregation_id
    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd2",
        verbosity="INFO",
        aggregation_id="1234",
    )
    newmeta = aggdata.generate_metadata(aggr_mean)
    logger.debug("New metadata:\n%s", utils.prettyprint_dict(newmeta))
    assert newmeta["fmu"]["aggregation"]["id"] == "1234"

    # Raise when given aggregation_id is not a string 1
    with pytest.raises(ValueError):
        aggdata = dataio.AggregatedData(
            source_metadata=metas,
            operation="mean",
            name="myaggrd2",
            verbosity="INFO",
            aggregation_id=True,
        )
        newmeta = aggdata.generate_metadata(aggr_mean)

    # Raise when given aggregation_id is not a string 2
    with pytest.raises(ValueError):
        aggdata = dataio.AggregatedData(
            source_metadata=metas,
            operation="mean",
            name="myaggrd2",
            verbosity="INFO",
        )
        newmeta = aggdata.generate_metadata(aggr_mean, aggregation_id=True)


def test_generate_aggr_uuid(fmurun_w_casemetadata, aggr_surfs_mean):
    """Test the _generate_aggr_uuid private method."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    aggr_mean, metas = aggr_surfs_mean  # xtgeo_object, list-of-metadata-dicts
    logger.info("Aggr. mean is %s", aggr_mean.values.mean())  # shall be 1238.5

    # let missing aggregation_id argument generate the id
    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd2",
        verbosity="INFO",
    )

    # Sorting shall be ignored
    agg_uuid_1 = aggdata._generate_aggr_uuid(["a", "b", "c"])
    agg_uuid_2 = aggdata._generate_aggr_uuid(["c", "a", "b"])
    assert agg_uuid_1 == agg_uuid_2

    # Different input shall give different result
    agg_uuid_1 = aggdata._generate_aggr_uuid(["a", "b", "c"])
    agg_uuid_2 = aggdata._generate_aggr_uuid(["c", "a", "b", "e"])
    assert agg_uuid_1 != agg_uuid_2

    # Returned value shall be a string
    assert isinstance(agg_uuid_1, str), str(type(agg_uuid_1))


def test_regsurf_aggregated_diffdata(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test surfaces, where input is diffdata."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
    )

    aggs = []
    # create "forward" files
    for i in range(10):
        use_regsurf = regsurf.copy()
        use_regsurf.values += float(i)
        expfile = edata.export(
            use_regsurf,
            name="mymap_" + str(i),
            realization=i,
            timedata=[[20300201], [19990204]],
        )
        aggs.append(expfile)

    # next task is to do an aggradation, and now the metadata already exists
    # per input element which shall be re-used
    surfs = xtgeo.Surfaces()
    metas = []
    for mapfile in aggs:
        surf = xtgeo.surface_from_file(mapfile)
        meta = dataio.read_metadata(mapfile)

        metas.append(meta)
        surfs.append([surf])

    aggregated = surfs.statistics()
    logger.info("Aggr. mean is %s", aggregated["mean"].values.mean())  # shall be 1238.5

    aggdata = dataio.AggregatedData(
        source_metadata=metas,
        operation="mean",
        name="myaggrd",
        verbosity="INFO",
        aggregation_id="789politipoliti",
    )
    newmeta = aggdata.generate_metadata(aggregated["mean"])
    logger.info("New metadata:\n%s", utils.prettyprint_dict(newmeta))
