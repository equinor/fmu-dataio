import os
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import xtgeo
from pandas import DataFrame

import fmu.dataio.load.load_standard_results as load_standard_results

TEST_UUID = "00000000-0000-0000-0000-000000000000"


def _generate_metadata_mock(
    case_name: str = "mock_case",
    realization_name: str = "realization-0",
    ensemble_name: str = "iter-0",
    data_name: str = "test_data",
    standard_result_name: str = "inplace_volumes",
    data_type: str = "tables",
) -> dict:
    relative_path = (
        f"{realization_name}/"
        f"{ensemble_name}/"
        f"share/results"
        f"{data_type}/"
        f"{standard_result_name}/"
        f"{data_name}.parquet"
    )

    return {
        "fmu": {
            "case": {"name": case_name},
            "realization": {"name": realization_name},
            "ensemble": {"name": ensemble_name},
        },
        "data": {
            "name": data_name,
            "standard_result": {
                "name": standard_result_name,
                "file_schema": {"url": "http://test.com"},
            },
        },
        "file": {"relative_path": relative_path},
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
            TEST_UUID, "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_ids = inplace_volumes.list_realizations()
        assert get_realizations_mock.assert_called_once

        assert actual_ids == realization_ids


def test_get_blobs(unregister_pandas_parquet):
    mocked_data_frame = pd.DataFrame(columns=["FLUID", "ZONE", "REGION", "GIIP"])
    mocked_blob = BytesIO()
    mocked_data_frame.to_parquet(mocked_blob)

    data_name_mock = "simgrid"
    mocked_metadata = _generate_metadata_mock(
        data_name=data_name_mock, standard_result_name="inplace_volumes"
    )

    mocked_blobs_with_metadata: list[tuple[BytesIO, dict]] = [
        (mocked_blob, mocked_metadata)
    ]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_blobs_with_metadata",
            return_value=mocked_blobs_with_metadata,
        ) as get_blobs_mock,
    ):
        inplace_volumes_loader = load_standard_results.load_inplace_volumes(
            TEST_UUID, "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_blobs_dict = inplace_volumes_loader.get_blobs(0)
        assert get_blobs_mock.assert_called_once
        assert len(actual_blobs_dict) == len(mocked_blobs_with_metadata)

        blob_name = list(actual_blobs_dict.keys())[0]
        assert blob_name == data_name_mock

        actual_blob = actual_blobs_dict[blob_name]
        actual_data_frame = pd.read_parquet(actual_blob)
        pd.testing.assert_frame_equal(actual_data_frame, mocked_data_frame)


def test_get_realization():
    columns = ["FLUID", "ZONE", "REGION", "GIIP"]
    mocked_data_frame = pd.DataFrame(columns=columns)

    data_name_mock = "geogrid"
    mocked_metadata = _generate_metadata_mock(
        data_name=data_name_mock, standard_result_name="inplace_volumes"
    )

    mocked_objects_with_metadata: list[tuple[DataFrame, dict]] = [
        (mocked_data_frame, mocked_metadata)
    ]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_objects_with_metadata",
            return_value=mocked_objects_with_metadata,
        ) as get_realizations_mock,
    ):
        inplace_volumes_loader = load_standard_results.load_inplace_volumes(
            TEST_UUID, "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_data_dict = inplace_volumes_loader.get_realization(0)
        assert get_realizations_mock.assert_called_once
        assert len(actual_data_dict) == len(mocked_objects_with_metadata)

        data_frame_name = list(actual_data_dict.keys())[0]
        assert data_frame_name == data_name_mock

        pd.testing.assert_frame_equal(
            actual_data_dict[data_frame_name], mocked_data_frame
        )


def test_save_realization_for_tabular(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    columns = ["FLUID", "ZONE", "REGION", "GIIP"]
    mocked_data_frame = pd.DataFrame(columns=columns)

    case_name_mock = "test_case_tabular"
    data_name_mock = "simgrid"
    data_type = "tables"
    standard_result_name = "inplace_volumes"
    mocked_metadata = _generate_metadata_mock(
        case_name=case_name_mock,
        data_name=data_name_mock,
        standard_result_name=standard_result_name,
        data_type=data_type,
    )
    relative_path_mocked = Path(mocked_metadata["file"]["relative_path"])

    mocked_realization_data: list[tuple[DataFrame, dict]] = [
        (mocked_data_frame, mocked_metadata)
    ]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_objects_with_metadata",
            return_value=mocked_realization_data,
        ) as get_realization_with_metadata_mock,
        patch(
            "fmu.dataio.external_interfaces.schema_validation_interface.SchemaValidationInterface.validate_against_schema",
            return_value=True,
        ) as validate_object_mock,
    ):
        inplace_volumes_loader = load_standard_results.load_inplace_volumes(
            TEST_UUID, "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_file_paths = inplace_volumes_loader.save_realization(0, tmp_path)
        assert get_realization_with_metadata_mock.assert_called_once
        assert validate_object_mock.assert_called_once

        expected_relative_file_path = str(relative_path_mocked).replace(
            relative_path_mocked.suffix, ".csv"
        )
        expected_file_path = (
            f"{tmp_path}/{case_name_mock}/{expected_relative_file_path}"
        )

        assert actual_file_paths[0] == expected_file_path
        assert os.path.exists(expected_file_path)
        with open(expected_file_path) as file:
            content = file.read()
            assert "FLUID,ZONE,REGION,GIIP" in content


def test_save_realization_for_ploygons(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    polygon = xtgeo.Polygons()

    case_name_mock = "test_case_polygons"
    data_name_mock = "field_outline"
    data_type = "polygons"
    standard_result_name = "field_outlines"
    mocked_metadata = _generate_metadata_mock(
        case_name=case_name_mock,
        data_name=data_name_mock,
        standard_result_name=standard_result_name,
        data_type=data_type,
    )
    relative_path_mocked = Path(mocked_metadata["file"]["relative_path"])

    mocked_realization_data: list[tuple[xtgeo.Polygons, dict]] = [
        (polygon, mocked_metadata)
    ]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_objects_with_metadata",
            return_value=mocked_realization_data,
        ) as get_realization_with_metadata_mock,
        patch(
            "fmu.dataio.external_interfaces.schema_validation_interface.SchemaValidationInterface.validate_against_schema",
            return_value=True,
        ) as validate_object_mock,
    ):
        field_outlines_loader = load_standard_results.load_field_outlines(
            TEST_UUID, "some_ensemble_name"
        )
        assert class_init_mock.assert_called_once

        actual_file_paths = field_outlines_loader.save_realization(0, tmp_path)
        assert get_realization_with_metadata_mock.assert_called_once
        assert validate_object_mock.assert_called_once

        expected_relative_file_path = str(relative_path_mocked).replace(
            relative_path_mocked.suffix, ".csv"
        )
        expected_file_path = (
            f"{tmp_path}/{case_name_mock}/{expected_relative_file_path}"
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

    case_name_mock = "test_case_surfaces"
    data_name_mock = "basevolantis"
    standard_result_name = "structure_depth_surface"
    data_type = "maps"
    mocked_metadata = _generate_metadata_mock(
        case_name=case_name_mock,
        data_name=data_name_mock,
        standard_result_name=standard_result_name,
        data_type=data_type,
    )

    relative_path_mocked = Path(mocked_metadata["file"]["relative_path"])

    mocked_realization_data: list[tuple[xtgeo.Polygons, dict]] = [
        (surface, mocked_metadata)
    ]

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ) as class_init_mock,
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.get_objects_with_metadata",
            return_value=mocked_realization_data,
        ) as get_realization_with_metadata_mock,
        patch(
            "fmu.dataio.external_interfaces.schema_validation_interface.SchemaValidationInterface.validate_against_schema",
            return_value=True,
        ) as validate_object_mock,
    ):
        structure_depth_surface_loader = (
            load_standard_results.load_structure_depth_surfaces(
                TEST_UUID, "some_ensemble_name"
            )
        )
        assert class_init_mock.assert_called_once

        actual_file_paths = structure_depth_surface_loader.save_realization(0, tmp_path)
        assert get_realization_with_metadata_mock.assert_called_once
        assert validate_object_mock.assert_not_called

        expected_relative_file_path = str(relative_path_mocked).replace(
            relative_path_mocked.suffix, ".gri"
        )
        expected_file_path = (
            f"{tmp_path}/{case_name_mock}/{expected_relative_file_path}"
        )

        assert actual_file_paths[0] == expected_file_path
        assert os.path.exists(expected_file_path)

        surface_from_file = xtgeo.surface_from_file(
            expected_file_path, fformat="irap_binary"
        )
        assert round(surface_from_file.xinc, 3) == 0.319
        assert round(surface_from_file.yinc, 3) == 0.211


def test_construct_object_key():
    data_name_mock = "Valysar Fm."
    fluid_contact_type_mock = "goc"

    mocked_metadata = _generate_metadata_mock(
        data_name=data_name_mock, standard_result_name="fluid_contact_surface"
    )
    mocked_metadata["data"].update(
        {"fluid_contact": {"contact": fluid_contact_type_mock}}
    )

    with (
        patch(
            "fmu.dataio.external_interfaces.sumo_explorer_interface.SumoExplorerInterface.__init__",
            return_value=None,
        ),
    ):
        fluid_contact_surfaces_loader = (
            load_standard_results.load_fluid_contact_surfaces(
                TEST_UUID, "some_ensemble_name"
            )
        )

        expected_object_key = (
            f"{data_name_mock.lower().replace(' ', '_').replace('.', '')}-"
            f"{fluid_contact_type_mock}"
        )
        actual_object_key = fluid_contact_surfaces_loader._construct_object_key(
            mocked_metadata
        )
        assert actual_object_key == expected_object_key
