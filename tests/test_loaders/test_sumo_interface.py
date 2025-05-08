import os
from unittest.mock import patch

import pandas as pd
import pytest

from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface
from fmu.sumo.explorer import Explorer
from fmu.sumo.explorer.objects import Case


@pytest.fixture
def sumo_test_case() -> Case:
    sumo_access_token = os.environ.get("SUMO_ACCESS_TOKEN")
    test_case_id = "3ca4b782-c8e8-4f77-9a75-d6a576751123"
    sumo_explorer = Explorer(env="dev", token=sumo_access_token)
    return sumo_explorer.get_case_by_uuid(test_case_id)


def test_initialize_inplace_volumes(sumo_test_case):
    ensemble_name = "iter-0"

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_test_case),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id", ensemble_name, "inplace_volumes"
        )

        for table in sumo_interface._search_context:
            assert (
                "inplace_volumes" in table.metadata["data"]["standard_result"]["name"]
            )

        expected_search_context = sumo_test_case.filter(
            iteration=ensemble_name, standard_result="inplace_volumes"
        )

        assert sumo_interface._search_context.columns == expected_search_context.columns
        assert (
            sumo_interface._search_context.contents == expected_search_context.contents
        )
        assert (
            sumo_interface._search_context.dataformats
            == expected_search_context.dataformats
        )
        assert sumo_interface._search_context.names == expected_search_context.names


def test_get_realization_ids(sumo_test_case):
    ensemble_name = "iter-0"

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_test_case),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id", ensemble_name, "inplace_volumes"
        )
        realization_ids = sumo_interface.get_realization_ids()

        expected_realization_ids = sumo_test_case.filter(
            iteration=ensemble_name, standard_result="inplace_volumes"
        ).realizationids

        assert realization_ids == expected_realization_ids


def test_get_realization(sumo_test_case):
    ensemble_name = "iter-0"
    realization_id = 0

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_test_case),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id", ensemble_name, "inplace_volumes"
        )

        expected_data = sumo_test_case.filter(
            iteration=ensemble_name,
            standard_result="inplace_volumes",
            realization=realization_id,
        )

        expected_first_data_frame = expected_data[0].to_pandas()
        expected_second_data_frame = expected_data[1].to_pandas()
        expected_first_name = expected_data[0].name
        expected_second_name = expected_data[1].name

        actual_data = sumo_interface.get_realization(realization_id)

        pd.testing.assert_frame_equal(
            actual_data[expected_first_name],
            expected_first_data_frame,
        )
        pd.testing.assert_frame_equal(
            actual_data[expected_second_name], expected_second_data_frame
        )

        with pytest.raises(AssertionError, match="DataFrame are different"):
            pd.testing.assert_frame_equal(
                expected_first_data_frame, actual_data[expected_second_name]
            )


def test_get_blob(sumo_test_case):
    ensemble_name = "iter-0"
    realization_id = 0

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_test_case),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id", ensemble_name, "inplace_volumes"
        )

        expected_data = sumo_test_case.filter(
            iteration=ensemble_name,
            standard_result="inplace_volumes",
            realization=realization_id,
        )
        expected_first_blob = expected_data[0].blob
        expected_second_blob = expected_data[1].blob
        expected_first_name = expected_data[0].name
        expected_second_name = expected_data[1].name

        actual_data = sumo_interface.get_blob(realization_id)

        assert (
            actual_data[expected_first_name].getvalue()
            == expected_first_blob.getvalue()
        )
        assert (
            actual_data[expected_second_name].getvalue()
            == expected_second_blob.getvalue()
        )


def test_get_realization_with_metadata(sumo_test_case):
    ensemble_name = "iter-0"
    realization_id = 0

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_test_case),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id", ensemble_name, "inplace_volumes"
        )

        expected_data = sumo_test_case.filter(
            iteration=ensemble_name,
            standard_result="inplace_volumes",
            realization=realization_id,
        )

        expected_first_metadata = expected_data[0].metadata
        expected_second_metadata = expected_data[1].metadata

        actual_data = sumo_interface.get_realization_with_metadata(realization_id)

        assert actual_data[0][1] == expected_first_metadata
        assert actual_data[1][1] == expected_second_metadata
