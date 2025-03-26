from copy import deepcopy
from unittest.mock import patch

import fmu.dataio.loaders.load_standard_results as load_standard_results


def test_load_inplace_volumes(metadata_examples):
    test_case = "005140af-cdc5-448c-9f34-84bcbb3f504d"

    product = {
        "name": "inplace_volumes",
        "file_schema": {
            "version": "0.1.0",
            "url": "https://main-fmu-schemas-prod.radix.equinor.com/schemas/file_formats/0.1.0/inplace_volumes.json",
        },
    }

    inplace_volume = deepcopy(metadata_examples["table_inplace_volumes.yml"])

    inplace_volume["data"]["product"] = product
    tables = [inplace_volume]

    with (
        patch(
            "fmu.external.sumo_explorer_interface.SumoExplorerInterface.__post_init__",
            return_value=None,
        ),
        patch(
            "fmu.external.sumo_explorer_interface.SumoExplorerInterface.get_volume_table_metadata",
            return_value=tables,
        ),
    ):
        inplace_volumes_standard_results = load_standard_results.load_inplace_volumes(
            test_case
        )
        assert len(inplace_volumes_standard_results) == 1


def test_load_structure_depth_surfaces():
    # Add tests
    assert True
