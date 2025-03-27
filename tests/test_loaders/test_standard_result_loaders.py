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

    volumes_table = deepcopy(metadata_examples["table_inplace_volumes.yml"])

    volumes_table["data"]["product"] = product
    volume_tables_metadata = [volumes_table]

    with (
        patch(
            "fmu.external.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ),
        patch(
            "fmu.external.sumo_explorer_interface.SumoExplorerInterface.get_inplace_volumes_standard_results",
            return_value=volume_tables_metadata,
        ),
        patch(
            "fmu.external.schema_validation_interface.SchemaValidationInterface.validate_against_schema",
            return_value=True,
        ),
    ):
        inplace_volumes_standard_results = load_standard_results.load_inplace_volumes(
            test_case
        )
        assert len(inplace_volumes_standard_results) == 1
        assert inplace_volumes_standard_results == volume_tables_metadata


def test_load_structure_depth_surfaces():
    # Add tests
    assert True
