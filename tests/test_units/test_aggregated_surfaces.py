"""Test the dataio running with aggregated surface."""
import logging
import os

import xtgeo

import fmu.dataionew._utils as utils
import fmu.dataionew.dataionew as dataio

logger = logging.getLogger(__name__)


def test_regsurf_aggregated(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test generating aggragated metadata for a surface, where input has metadata."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
        verbosity="INFO",
    )

    aggs = []
    # create "forward" files
    for i in range(1):  # TODO! 10
        use_regsurf = regsurf.copy()
        use_regsurf.values += float(i)
        expfile = edata.export(use_regsurf, name="mymap_" + str(i), realization=i)
        aggs.append(expfile)

    # next task is to do an aggradation, and now the metadata already exists
    # per input element which shall be re-used
    surfs = xtgeo.Surfaces()
    metas = []
    for mapfile in aggs:
        surf = xtgeo.surface_from_file(mapfile)
        meta = dataio.read_metadata(mapfile)
        print(utils.prettyprint_dict(meta))

        metas.append(meta)
        surfs.append([surf])

    aggregated = surfs.statistics()
    logger.info("Aggr. mean is %s", aggregated["mean"].values.mean())  # shall be 1238.5

    aggdata = dataio.AggregatedData(
        configs=metas,
        operation="mean",
        name="myaggrd",
        verbosity="INFO",
        aggregation_id="1234",
    )
    newmeta = aggdata.generate_aggregation_metadata(aggregated["mean"])
    logger.info("New metadata:\n%s", utils.prettyprint_dict(newmeta))


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
        configs=metas,
        operation="mean",
        name="myaggrd",
        verbosity="INFO",
        aggregation_id="789politipoliti",
    )
    newmeta = aggdata.generate_aggregation_metadata(aggregated["mean"])
    logger.info("New metadata:\n%s", utils.prettyprint_dict(newmeta))
