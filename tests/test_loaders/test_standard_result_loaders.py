import os
from io import BytesIO
from unittest.mock import patch

import pandas as pd
import xtgeo
from pandas import DataFrame

import fmu.dataio.load.load_standard_results as load_standard_results


def _generate_metadata_mock(
    case_name_mock: str,
    realization_name_mock: str,
    ensemble_name_mock: str,
    data_name_mock: str,
    standard_result_name: str,
) -> dict:
    return {
        "fmu": {
            "case": {"name": case_name_mock},
            "realization": {"name": realization_name_mock},
            "ensemble": {"name": ensemble_name_mock},
        },
        "data": {
            "name": data_name_mock,
            "standard_result": {
                "name": standard_result_name,
                "file_schema": {"url": "http://test.com"},
            },
        },
    }


def test_list_realizations():
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


def test_get_blobs(unregister_pandas_parquet):
    mocked_data_frame = pd.DataFrame(columns=["FLUID", "ZONE", "REGION", "GIIP"])

    buffer = BytesIO()
    mocked_data_frame.to_parquet(buffer)
    blob = buffer.getvalue()
    mocked_blobs_dict = {"test_blob_name": blob}

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_blobs",
            return_value=mocked_blobs_dict,
        ) as get_blobs_mock,
    ):
        inplace_volumes_loader = load_standard_results.load_inplace_volumes(
            "test_id", "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_blobs_dict = inplace_volumes_loader.get_blobs(0)
        assert get_blobs_mock.assert_called_once
        assert len(actual_blobs_dict) == len(mocked_blobs_dict)

        blob_name = list(actual_blobs_dict.keys())[0]
        assert blob_name == "test_blob_name"

        actual_blob = actual_blobs_dict[blob_name]
        actual_data_frame = pd.read_parquet(BytesIO(actual_blob))
        pd.testing.assert_frame_equal(actual_data_frame, mocked_data_frame)


def test_get_realization():
    columns = ["FLUID", "ZONE", "REGION", "GIIP"]
    mocked_data_frame = pd.DataFrame(columns=columns)
    mocked_realization_dict = {"test_volume": mocked_data_frame}

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_realization",
            return_value=mocked_realization_dict,
        ) as get_realizations_mock,
    ):
        inplace_volumes_loader = load_standard_results.load_inplace_volumes(
            "test_id", "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        realization_dict = inplace_volumes_loader.get_realization(0)
        assert get_realizations_mock.assert_called_once
        assert len(realization_dict) == len(mocked_realization_dict)

        data_frame_name = list(realization_dict.keys())[0]
        assert data_frame_name == "test_volume"

        data_frame = realization_dict[data_frame_name]
        pd.testing.assert_frame_equal(
            data_frame, mocked_realization_dict["test_volume"]
        )


def test_save_realization_for_tabular(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    columns = ["FLUID", "ZONE", "REGION", "GIIP"]
    mocked_data_frame = pd.DataFrame(columns=columns)

    case_name_mock = "test_case"
    realization_name_mock = "realization-0"
    ensemble_name_mock = "iter-0"
    data_name_mock = "tabular_object_name"
    standard_result_name = "inplace_volumes"
    mocked_metadata = _generate_metadata_mock(
        case_name_mock,
        realization_name_mock,
        ensemble_name_mock,
        data_name_mock,
        standard_result_name,
    )

    mocked_realization_data: list[tuple[DataFrame, dict]] = [
        (mocked_data_frame, mocked_metadata)
    ]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_realization_with_metadata",
            return_value=mocked_realization_data,
        ) as get_realization_with_metadata_mock,
        patch(
            "fmu.dataio.external_interfaces.schema_validation_interface.SchemaValidationInterface.validate_against_schema",
            return_value=True,
        ) as validate_object_mock,
    ):
        inplace_volumes_loader = load_standard_results.load_inplace_volumes(
            "test_id", "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_file_paths = inplace_volumes_loader.save_realization(0, tmp_path)
        assert get_realization_with_metadata_mock.assert_called_once
        assert validate_object_mock.assert_called_once

        expected_file_path = (
            f"{tmp_path}/"
            f"{case_name_mock}/"
            f"{realization_name_mock}/"
            f"{ensemble_name_mock}/"
            f"{standard_result_name}-{data_name_mock}.csv"
        )
        assert actual_file_paths[0] == expected_file_path
        assert os.path.exists(expected_file_path)

        with open(expected_file_path) as file:
            content = file.read()
            assert "FLUID,ZONE,REGION,GIIP" in content


def test_save_realization_for_ploygons(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    polygon = xtgeo.Polygons()

    case_name_mock = "test_case"
    realization_name_mock = "realization-0"
    ensemble_name_mock = "iter-0"
    data_name_mock = "polygon_object_name"
    standard_result_name = "field_outlines"
    mocked_metadata = _generate_metadata_mock(
        case_name_mock,
        realization_name_mock,
        ensemble_name_mock,
        data_name_mock,
        standard_result_name,
    )

    mocked_realization_data: list[tuple[xtgeo.Polygons, dict]] = [
        (polygon, mocked_metadata)
    ]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_realization_with_metadata",
            return_value=mocked_realization_data,
        ) as get_realization_with_metadata_mock,
        patch(
            "fmu.dataio.external_interfaces.schema_validation_interface.SchemaValidationInterface.validate_against_schema",
            return_value=True,
        ) as validate_object_mock,
    ):
        field_outlines_loader = load_standard_results.load_field_outlines(
            "test_id", "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_file_paths = field_outlines_loader.save_realization(0, tmp_path)
        assert get_realization_with_metadata_mock.assert_called_once
        assert validate_object_mock.assert_called_once

        expected_file_path = (
            f"{tmp_path}/"
            f"{case_name_mock}/"
            f"{realization_name_mock}/"
            f"{ensemble_name_mock}/"
            f"{standard_result_name}-{data_name_mock}.csv"
        )
        assert actual_file_paths[0] == expected_file_path
        assert os.path.exists(expected_file_path)

        with open(expected_file_path) as file:
            content = file.read()
            assert "X_UTME,Y_UTMN,Z_TVDSS" in content


def test_save_realization_for_surfaces(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    surface = xtgeo.RegularSurface(
        ncol=1,
        nrow=1,
        xinc=0.319,
        yinc=0.211,
    )

    case_name_mock = "test_case"
    realization_name_mock = "realization-0"
    ensemble_name_mock = "iter-0"
    data_name_mock = "surface_object_name"
    standard_result_name = "structure_depth_surface"
    mocked_metadata = _generate_metadata_mock(
        case_name_mock,
        realization_name_mock,
        ensemble_name_mock,
        data_name_mock,
        standard_result_name,
    )

    mocked_realization_data: list[tuple[xtgeo.Polygons, dict]] = [
        (surface, mocked_metadata)
    ]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_realization_with_metadata",
            return_value=mocked_realization_data,
        ) as get_realization_with_metadata_mock,
        patch(
            "fmu.dataio.external_interfaces.schema_validation_interface.SchemaValidationInterface.validate_against_schema",
            return_value=True,
        ) as validate_object_mock,
    ):
        structure_depth_surface_loader = (
            load_standard_results.load_structure_depth_surfaces(
                "test_id", "some_ensemble_name"
            )
        )
        assert class_init_mock.assert_called_once

        actual_file_paths = structure_depth_surface_loader.save_realization(0, tmp_path)
        assert get_realization_with_metadata_mock.assert_called_once
        assert validate_object_mock.assert_not_called

        expected_file_path = (
            f"{tmp_path}/"
            f"{case_name_mock}/"
            f"{realization_name_mock}/"
            f"{ensemble_name_mock}/"
            f"{standard_result_name}-{data_name_mock}.gri"
        )

        assert actual_file_paths[0] == expected_file_path
        assert os.path.exists(expected_file_path)

        surface_from_file = xtgeo.surface_from_file(
            expected_file_path, fformat="irap_binary"
        )
        assert round(surface_from_file.xinc, 3) == 0.319
        assert round(surface_from_file.yinc, 3) == 0.211
