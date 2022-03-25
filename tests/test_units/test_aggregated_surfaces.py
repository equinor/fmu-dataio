"""Test the dataio running with aggregated surface.

CURRENTLY IN DEVELOPMENT!

"""
import logging
import os

import pytest
import xtgeo

import fmu.dataionew.dataionew as dataio

logger = logging.getLogger(__name__)


def test_regsurf_aggregated(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test generating aggragated metadata for a surface, where input has metadata."""
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
        expfile = edata.export(use_regsurf, name="mymap_" + str(i))
        aggs.append(expfile)

    # next task is to do an aggradation, and now the metadata already exists
    # which shall be re-used
    surfs = xtgeo.Surfaces()
    metas = []
    for mapfile in aggs:
        surf = xtgeo.surface_from_file(mapfile)
        meta = dataio.read_metadata(mapfile)

        metas.append(meta)
        surfs.append([surf])

    aggregated = surfs.statistics()
    logger.info("Aggr. mean is %s", aggregated["mean"].values.mean())  # shall be 1238.5

    # the comes the dataio interface...
    # Decisions:
    # - own class or just a flag in ExportData?
    # - How to treat existing metadata?
    # - Should it be possible to override existing metadata?
    # - Should it be possible with aggregations that do not have
    #   have existing metdata files?

    with pytest.raises(NotImplementedError):
        aggdata = dataio.ExportData(
            config=metas[0],  # be able to "sniff" that the config is template metadata?
            aggregation=True,
        )
        aggdata.export(aggregated["mean"])
