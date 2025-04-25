from unittest.mock import patch

import pandas as pd
import pytest

import fmu.dataio.load.load_standard_results as load_standard_results


def test_inplace_volumes_list_realizations():
    realization_ids = [0, 1, 2, 3]
    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_realization_ids",
            return_value=realization_ids,
        ) as get_realizations_mock,
    ):
        inplace_volumes = load_standard_results.load_inplace_volumes(
            "test_id", "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_ids = inplace_volumes.list_realizations()
        assert get_realizations_mock.assert_called_once

        assert actual_ids == realization_ids


def test_inplace_volumes_get_realization():
    columns = ["FLUID", "ZONE", "REGION", "GIIP"]
    data_frame = pd.DataFrame(columns=columns)

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_realization",
            return_value=[data_frame],
        ) as get_realizations_mock,
    ):
        inplace_volumes = load_standard_results.load_inplace_volumes(
            "test_id", "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        data_frames = inplace_volumes.get_realization(0)
        assert get_realizations_mock.assert_called_once

        actual_data_frame = data_frames[0]

        pd.testing.assert_frame_equal(actual_data_frame, data_frame)

        assert actual_data_frame.FLUID.name
        assert actual_data_frame.ZONE.name
        assert actual_data_frame.REGION.name
        assert actual_data_frame.GIIP.name
        with pytest.raises(
            AttributeError, match="'DataFrame' object has no attribute 'STOIIP'"
        ):
            assert actual_data_frame.STOIIP


def test_inplace_volumes_save_realization(tmp_path):
    # TODO
    assert True


def test_inplace_volumes_get_blob():
    # TODO
    assert True
