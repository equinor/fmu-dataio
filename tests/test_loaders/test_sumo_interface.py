from unittest.mock import patch

import pandas as pd
import pytest

from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface
from fmu.sumo.explorer import Explorer
from fmu.sumo.explorer.objects import Case


@pytest.fixture
def sumo_test_case() -> Case:
    # This should be replaced by test_data stored locally.
    # Fetching directly from Sumo for now
    test_case_id = "3ca4b782-c8e8-4f77-9a75-d6a576751123"
    sumo = Explorer(env="dev")
    return sumo.get_case_by_uuid(test_case_id)


@pytest.mark.skip(
    reason="Authentication towards sumo not working from github workflow yet."
)
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


@pytest.mark.skip(
    reason="Authentication towards sumo not working from github workflow yet."
)
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


@pytest.mark.skip(
    reason="Authentication towards sumo not working from github workflow yet."
)
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

        expected_realization_inplace_volumes = sumo_test_case.filter(
            iteration=ensemble_name,
            standard_result="inplace_volumes",
            realization=realization_id,
        )

        expected_first_data_frame = expected_realization_inplace_volumes[0].to_pandas()
        expected_second_data_frame = expected_realization_inplace_volumes[1].to_pandas()

        expected_first_name = expected_realization_inplace_volumes[0].name
        expected_second_name = expected_realization_inplace_volumes[1].name

        realization_data_frames = sumo_interface.get_realization(realization_id)

        pd.testing.assert_frame_equal(
            realization_data_frames[expected_first_name],
            expected_first_data_frame,
        )
        pd.testing.assert_frame_equal(
            realization_data_frames[expected_second_name], expected_second_data_frame
        )

        with pytest.raises(AssertionError, match="DataFrame are different"):
            pd.testing.assert_frame_equal(
                expected_first_data_frame, realization_data_frames[expected_second_name]
            )


@pytest.mark.skip(
    reason="Authentication towards sumo not working from github workflow yet."
)
def test_get_blob():
    # TODO
    assert True


@pytest.mark.skip(
    reason="Authentication towards sumo not working from github workflow yet."
)
def test_get_realization_with_metadata():
    # TODO
    assert True


@pytest.mark.skip(
    reason="Authentication towards sumo not working from github workflow yet."
)
def test_get_depth_surface():
    # TODO
    assert True
