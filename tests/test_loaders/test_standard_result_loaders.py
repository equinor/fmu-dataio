from copy import deepcopy
from unittest.mock import MagicMock, patch

import fmu.dataio.load.load_standard_results as load_standard_results


def test_load_inplace_volumes(metadata_examples):
    test_case = "005140af-cdc5-448c-9f34-84bcbb3f504d"
    ensemble_name = "iter-0"

    product = {
        "name": "inplace_volumes",
        "file_schema": {
            "version": "0.1.0",
            "url": "https://main-fmu-schemas-prod.radix.equinor.com/schemas/file_formats/0.1.0/inplace_volumes.json",
        },
    }

    volumes_table_metadata = deepcopy(metadata_examples["table_inplace_volumes.yml"])
    volumes_table_metadata["data"]["product"] = product

    table_mock = MagicMock()
    table_mock.metadata = volumes_table_metadata
    volume_tables = [table_mock]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ),
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_volume_tables",
            return_value=volume_tables,
        ),
    ):
        inplace_volumes = load_standard_results.load_inplace_volumes(
            test_case, ensemble_name
        )

        assert len(inplace_volumes._inplace_volumes) == 1
        assert len(inplace_volumes._inplace_volumes_metadata) == 1
        assert inplace_volumes._inplace_volumes_metadata[0] == table_mock.metadata


def test_load_structure_depth_surfaces():
    # Add tests
    assert True
