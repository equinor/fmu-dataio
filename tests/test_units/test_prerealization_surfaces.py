"""Test the dataio running with pre-realization objects, e.g. surfaces.

These objects are normally made before ERT has ran forward jobs and are typically used
to compare results.
"""
import logging
import os

import fmu.dataionew._utils as utils
import fmu.dataionew.dataionew as dataio

logger = logging.getLogger(__name__)


def test_regsurf_prerealization(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test generating pre-realization surfaces."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
    )

    metadata = edata.generate_metadata(regsurf, name="mymap", pre_realizations=True)
