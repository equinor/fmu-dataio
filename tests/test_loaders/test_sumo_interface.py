from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import xtgeo
from pandas import DataFrame

from fmu.dataio._models.fmu_results.enums import FMUClass, StandardResultName
from fmu.dataio.external_interfaces.sumo_explorer_interface import SumoExplorerInterface
from fmu.sumo.explorer import Explorer


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
            FMUClass.table,
            StandardResultName.inplace_volumes,
        )

        actual_realization_ids = sumo_interface.get_realization_ids()
        assert actual_realization_ids == realization_ids_mock


def test_get_realalization():
    ensemble_name = "iter-0"
    realization_id = 0

    columns_mock = ["FLUID", "ZONE", "REGION", "GIIP"]
    data_frame_mock = pd.DataFrame(columns=columns_mock)

    sumo_table_object_mock = MagicMock()
    sumo_table_object_mock.name = "table_object_name"
    sumo_table_object_mock.to_pandas.return_value = data_frame_mock

    sumo_case_mock = _generate_sumo_case_mock(sumo_table_object_mock)

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_case_mock),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id",
            ensemble_name,
            FMUClass.table,
            StandardResultName.inplace_volumes,
        )

        actual_realization = sumo_interface.get_realization(realization_id)

        pd.testing.assert_frame_equal(
            actual_realization[sumo_table_object_mock.name],
            data_frame_mock,
        )


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
            FMUClass.table,
            StandardResultName.inplace_volumes,
        )

        actual_data = sumo_interface.get_realization_with_metadata(realization_id)

        pd.testing.assert_frame_equal(
            actual_data[0][0],
            data_frame_mock,
        )

        assert actual_data[0][1] == metadata_mock


def test_get_blobs():
    ensemble_name = "iter-0"
    realization_id = 0

    buffer = BytesIO(b"Test blob")
    mocked_blob = buffer.getvalue()

    sumo_table_object_mock = MagicMock()
    sumo_table_object_mock.name = "table_object_name"
    sumo_table_object_mock.blob = mocked_blob

    sumo_case_mock = _generate_sumo_case_mock(sumo_table_object_mock)

    with (
        patch.object(Explorer, "__init__", return_value=None),
        patch.object(Explorer, "get_case_by_uuid", return_value=sumo_case_mock),
    ):
        sumo_interface = SumoExplorerInterface(
            "some_case_id",
            ensemble_name,
            FMUClass.table,
            StandardResultName.inplace_volumes,
        )

        actual_blob_data = sumo_interface.get_blobs(realization_id)
        assert actual_blob_data[sumo_table_object_mock.name] == mocked_blob


def test_correct_data_format_returned(unregister_pandas_parquet):
    ensemble_name = "iter-0"
    realization_id = 0

    # Table class
    data_frame_mock = pd.DataFrame()
    sumo_table_object_mock = MagicMock()
    sumo_table_object_mock.name = "table_object_name"
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
            FMUClass.table,
            StandardResultName.inplace_volumes,
        )
        table_data = sumo_interface.get_realization(realization_id)
        for value in table_data.values():
            assert isinstance(value, DataFrame)

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
            FMUClass.polygons,
            StandardResultName.field_outline,
        )
        polygon_data = sumo_interface.get_realization(realization_id)
        for value in polygon_data.values():
            assert isinstance(value, xtgeo.Polygons)

    # Surfaces class
    mocked_surface = xtgeo.RegularSurface(
        ncol=1,
        nrow=1,
        xinc=0.1,
        yinc=0.1,
    )
    sumo_surface_object_mock = MagicMock()
    sumo_surface_object_mock.name = "surface_object_name"
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
            FMUClass.surface,
            StandardResultName.structure_depth_surface,
        )
        surface_data = sumo_interface.get_realization(realization_id)
        for value in surface_data.values():
            assert isinstance(value, xtgeo.RegularSurface)
