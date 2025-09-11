import os
from io import BytesIO
from unittest.mock import MagicMock, call, patch

import pandas as pd
import xtgeo
from fmu.datamodels.fmu_results.enums import ObjectMetadataClass
from fmu.datamodels.standard_results.enums import StandardResultName
from fmu.sumo.explorer import Explorer
from pandas import DataFrame

from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface


def _generate_sumo_case_mock(sumo_object_mock: MagicMock):
    summo_search_context_realization_mock = MagicMock()
    summo_search_context_realization_mock.__iter__.return_value = iter(
        [sumo_object_mock]
    )

    sumo_search_context_case_mock = MagicMock()
    sumo_search_context_case_mock.filter.return_value = (
        summo_search_context_realization_mock
    )

    sumo_case_mock = MagicMock()
    sumo_case_mock.filter.return_value = sumo_search_context_case_mock

    return sumo_case_mock


def test_get_realization_ids():
    ensemble_name = "iter-0"
    realization_ids_mock = [0, 16, 48]
    sumo_case_mock = MagicMock()
    search_context_mock = MagicMock()
    search_context_mock.realizationids = realization_ids_mock
    sumo_case_mock.filter.return_value = search_context_mock

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_case_mock),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id",
            ensemble_name,
            ObjectMetadataClass.table,
            StandardResultName.inplace_volumes,
        )

        actual_realization_ids = sumo_interface.get_realization_ids()
        assert actual_realization_ids == realization_ids_mock


def test_get_realization_with_metadata():
    ensemble_name = "iter-0"
    realization_id = 0

    columns_mock = ["FLUID", "ZONE", "REGION", "GIIP"]
    data_frame_mock = pd.DataFrame(columns=columns_mock)
    metadata_mock = {"name": "metadata_name"}

    sumo_table_object_mock = MagicMock()
    sumo_table_object_mock.name = "table_object_name"
    sumo_table_object_mock.to_pandas.return_value = data_frame_mock
    sumo_table_object_mock.metadata = metadata_mock

    sumo_case_mock = _generate_sumo_case_mock(sumo_table_object_mock)

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_case_mock),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id",
            ensemble_name,
            ObjectMetadataClass.table,
            StandardResultName.inplace_volumes,
        )

        actual_data = sumo_interface.get_objects_with_metadata(realization_id)

        pd.testing.assert_frame_equal(
            actual_data[0][0],
            data_frame_mock,
        )

        assert actual_data[0][1] == metadata_mock


def test_get_blobs():
    ensemble_name = "iter-0"
    realization_id = 0

    mocked_blob = BytesIO(b"Test blob")
    metadata_mock = {"name": "metadata_name"}

    sumo_table_object_mock = MagicMock()
    sumo_table_object_mock.name = "table_object_name"
    sumo_table_object_mock.blob = mocked_blob
    sumo_table_object_mock.metadata = metadata_mock

    sumo_case_mock = _generate_sumo_case_mock(sumo_table_object_mock)

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_case_mock),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id",
            ensemble_name,
            ObjectMetadataClass.table,
            StandardResultName.inplace_volumes,
        )

        actual_blob_data = sumo_interface.get_blobs_with_metadata(realization_id)
        assert len(actual_blob_data) == 1
        assert len(actual_blob_data[0]) == 2
        assert actual_blob_data[0][0] == mocked_blob
        assert actual_blob_data[0][1]["name"] == "metadata_name"


def test_correct_data_format_returned(unregister_pandas_parquet):
    ensemble_name = "iter-0"
    realization_id = 0
    metadata_mock = {}

    # Table class
    data_frame_mock = pd.DataFrame()
    sumo_table_object_mock = MagicMock()
    sumo_table_object_mock.name = "table_object_name"
    sumo_table_object_mock.metadata = metadata_mock
    sumo_table_object_mock.to_pandas.return_value = data_frame_mock
    sumo_case_with_table_mock = _generate_sumo_case_mock(sumo_table_object_mock)

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(
            Explorer, "get_case_by_uuid", return_value=sumo_case_with_table_mock
        ),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id",
            ensemble_name,
            ObjectMetadataClass.table,
            StandardResultName.inplace_volumes,
        )
        objects_with_metadata = sumo_interface.get_objects_with_metadata(realization_id)
        for object, _ in objects_with_metadata:
            assert isinstance(object, DataFrame)

    # Polygons class
    mocked_polygon = xtgeo.Polygons(
        [
            [1, 22, 3, 0],
            [6, 25, 4, 0],
            [8, 27, 6, 0],
            [1, 22, 3, 0],
        ]
    )
    mocked_data_frame = mocked_polygon.dataframe
    buffer = BytesIO()
    mocked_data_frame.to_parquet(buffer)
    mocked_blob = BytesIO(buffer.getvalue())
    sumo_polygon_object_mock = MagicMock()
    sumo_polygon_object_mock.name = "polygon_object_name"
    sumo_polygon_object_mock.blob = mocked_blob
    sumo_polygon_object_mock.metadata = metadata_mock
    sumo_case_with_polygon_mock = _generate_sumo_case_mock(sumo_polygon_object_mock)

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(
            Explorer, "get_case_by_uuid", return_value=sumo_case_with_polygon_mock
        ),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id",
            ensemble_name,
            ObjectMetadataClass.polygons,
            StandardResultName.field_outline,
        )
        objects_with_metadata = sumo_interface.get_objects_with_metadata(realization_id)
        for object, _ in objects_with_metadata:
            assert isinstance(object, xtgeo.Polygons)

    # Surfaces class
    mocked_surface = xtgeo.RegularSurface(
        ncol=1,
        nrow=1,
        xinc=0.1,
        yinc=0.1,
    )
    sumo_surface_object_mock = MagicMock()
    sumo_surface_object_mock.name = "surface_object_name"
    sumo_surface_object_mock.metadata = metadata_mock
    sumo_surface_object_mock.to_regular_surface.return_value = mocked_surface
    sumo_case_with_surface_mock = _generate_sumo_case_mock(sumo_surface_object_mock)

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(
            Explorer, "get_case_by_uuid", return_value=sumo_case_with_surface_mock
        ),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id",
            ensemble_name,
            ObjectMetadataClass.surface,
            StandardResultName.structure_depth_surface,
        )
        objects_with_metadata = sumo_interface.get_objects_with_metadata(realization_id)
        for object, _ in objects_with_metadata:
            assert isinstance(object, xtgeo.RegularSurface)


def test_use_sumo_dev_when_komodo_bleeding():
    sumo_table_object_mock = MagicMock()
    sumo_case_with_table_mock = _generate_sumo_case_mock(sumo_table_object_mock)
    os.environ["KOMODO_RELEASE"] = "bleeding-20250626-1456-py311-rhel8"

    with (
        patch.object(
            Explorer, "__init__", return_value=None
        ) as mock_sumo_explorer_init,
        patch.object(
            Explorer, "get_case_by_uuid", return_value=sumo_case_with_table_mock
        ),
    ):
        SumoExplorerInterface(
            "some_case_id",
            "iter-0",
            ObjectMetadataClass.polygons,
            StandardResultName.field_outline,
        )

        mock_sumo_explorer_init.assert_called_once()
        assert mock_sumo_explorer_init.call_args == call(env="dev")


def test_use_sumo_prod_when_komodo_stable():
    sumo_table_object_mock = MagicMock()
    sumo_case_with_table_mock = _generate_sumo_case_mock(sumo_table_object_mock)
    os.environ["KOMODO_RELEASE"] = "2025.06.02-py311-rhel8"

    with (
        patch.object(
            Explorer, "__init__", return_value=None
        ) as mock_sumo_explorer_init,
        patch.object(
            Explorer, "get_case_by_uuid", return_value=sumo_case_with_table_mock
        ),
    ):
        SumoExplorerInterface(
            "some_case_id",
            "iter-0",
            ObjectMetadataClass.polygons,
            StandardResultName.field_outline,
        )

        mock_sumo_explorer_init.assert_called_once()
        assert mock_sumo_explorer_init.call_args == call(env="prod")
