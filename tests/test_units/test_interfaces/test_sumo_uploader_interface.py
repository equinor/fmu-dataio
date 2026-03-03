"""Unit tests for SumoUploaderInterface."""

import io
from collections.abc import Generator
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from fmu.dataio._interfaces import (
    SUMO_CLIENT_ID,
    SumoUploaderInterface,
    pa_table_to_bytes,
)

pytest.importorskip(
    "fmu.sumo.uploader",
    reason="fmu-sumo-uploader is not installed",
)


@pytest.fixture
def simple_parameters() -> pa.Table:
    return pa.table(
        {
            "REAL": pa.array([0, 1, 2], type=pa.int64()),
            "value": [1.0, 2.0, 3.0],
        }
    )


@pytest.fixture
def simple_metadata() -> dict[str, Any]:
    return {
        "file": {
            "relative_path": "share/results/ensemble/iter-0/tables/parameters.parquet",
            "data": {
                "content": "parameters",
            },
        }
    }


@pytest.fixture
def mock_uploader() -> Generator[SumoUploaderInterface]:
    with patch("fmu.sumo.uploader.SumoConnection"):
        yield SumoUploaderInterface("prod", "uuid-1", Path("global_variables.yml"))


def test_pa_table_to_bytes_returns_bytes(simple_parameters: pa.Table) -> None:
    """Ensure bytes are returned."""
    result = pa_table_to_bytes(simple_parameters)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_pa_table_to_bytes_roundtrip(simple_parameters: pa.Table) -> None:
    """Binary table can be restored to a proper table."""
    result = pa_table_to_bytes(simple_parameters)
    restored = pq.read_table(io.BytesIO(result))
    assert restored.equals(simple_parameters)


def test_init_creates_sumo_connection() -> None:
    """A Sumo connection is created with values instantiated."""
    mock_conn = MagicMock()
    with patch("fmu.sumo.uploader.SumoConnection", return_value=mock_conn) as mock_cls:
        uploader = SumoUploaderInterface(
            env="prod", case_uuid="uuid-123", global_config_path=Path("/some/path")
        )

    mock_cls.assert_called_once_with(
        "prod", case_uuid="uuid-123", client_id=uploader.client_id
    )
    assert uploader.env == "prod"
    assert uploader.case_uuid == "uuid-123"
    assert uploader.connection is mock_conn
    assert uploader._queue == []


def test_init_uses_default_client_id(mock_uploader: SumoUploaderInterface) -> None:
    """Sumo provides a client id to connect uploads: ensure it is used."""
    assert mock_uploader.client_id == SUMO_CLIENT_ID


def test_init_accepts_custom_client_id() -> None:
    """Ensure a custom id can be accepted, just in case."""
    with patch("fmu.sumo.uploader.SumoConnection"):
        uploader = SumoUploaderInterface(
            "prod", "uuid-1", Path("/p"), client_id="custom-id"
        )

    assert uploader.client_id == "custom-id"


def test_queue_table_appends_file_to_queue(
    simple_parameters: pa.Table,
    simple_metadata: dict[str, Any],
    mock_uploader: SumoUploaderInterface,
) -> None:
    """Ensure a queued table ends up in the queue."""
    with patch("fmu.sumo.uploader._fileonjob.FileOnJob") as mock_file_cls:
        mock_file = MagicMock()
        mock_file_cls.return_value = mock_file
        mock_uploader.queue_table(simple_parameters, simple_metadata)

    assert len(mock_uploader._queue) == 1
    assert mock_uploader._queue[0] == mock_file


def test_queue_table_sets_path_from_metadata(
    simple_parameters: pa.Table,
    simple_metadata: dict[str, Any],
    mock_uploader: SumoUploaderInterface,
) -> None:
    """Queue file function should set the file path to the relative path."""
    with patch("fmu.sumo.uploader._fileonjob.FileOnJob") as mock_file_cls:
        mock_file = MagicMock()
        mock_file_cls.return_value = mock_file
        mock_uploader.queue_table(simple_parameters, simple_metadata)

    assert mock_file.path == simple_metadata["file"]["relative_path"]


def test_queue_table_sets_empty_metadata_path(
    simple_parameters: pa.Table,
    simple_metadata: dict[str, Any],
    mock_uploader: SumoUploaderInterface,
) -> None:
    """Queue file method sets the metadata path to empty string."""
    with patch("fmu.sumo.uploader._fileonjob.FileOnJob") as mock_file_cls:
        mock_file = MagicMock()
        mock_file_cls.return_value = mock_file
        mock_uploader.queue_table(simple_parameters, simple_metadata)

    assert mock_file.metadata_path == ""


def test_queue_table_sets_size_equal_to_byte_string_length(
    simple_parameters: pa.Table,
    simple_metadata: dict[str, Any],
    mock_uploader: SumoUploaderInterface,
) -> None:
    """Queueing a file counts the number of bytes and sets them."""
    with patch("fmu.sumo.uploader._fileonjob.FileOnJob") as mock_file_cls:
        mock_file = MagicMock()
        mock_file_cls.return_value = mock_file
        mock_uploader.queue_table(simple_parameters, simple_metadata)

    assert mock_file.size == len(mock_file.byte_string)


def test_queue_table_multiple_calls_grow_queue(
    simple_parameters: pa.Table,
    simple_metadata: dict[str, Any],
    mock_uploader: SumoUploaderInterface,
) -> None:
    """Queueing multiple files grows the queue."""
    simple_metadata_b = deepcopy(simple_metadata)
    simple_metadata_b["file"]["relative_path"] = (
        "share/results/ensemble/tables/b.parquet"
    )

    with patch("fmu.sumo.uploader._fileonjob.FileOnJob") as mock_file_cls:
        mock_file = MagicMock()
        mock_file_cls.return_value = mock_file
        mock_uploader.queue_table(simple_parameters, simple_metadata)
        mock_file = MagicMock()
        mock_file_cls.return_value = mock_file
        mock_uploader.queue_table(simple_parameters, simple_metadata_b)

    assert len(mock_uploader._queue) == 2
    assert mock_uploader._queue[0].path == simple_metadata["file"]["relative_path"]
    assert mock_uploader._queue[1].path == simple_metadata_b["file"]["relative_path"]


def test_upload_calls_upload_files_with_correct_args(
    mock_uploader: SumoUploaderInterface,
) -> None:
    """Calling upload calls Sumo Uploader correctly."""
    mock_file = MagicMock()
    mock_uploader._queue = [mock_file]

    mock_result = {
        "ok_uploads": [mock_file],
        "failed_uploads": [],
        "rejected_uploads": [],
    }
    with patch(
        "fmu.sumo.uploader._upload_files.upload_files", return_value=mock_result
    ) as mock_upload:
        result = mock_uploader.upload()

    mock_upload.assert_called_once_with(
        [mock_file],
        "uuid-1",
        mock_uploader.connection,
        config_path=Path("global_variables.yml"),
    )
    assert result == mock_result


def test_upload_clears_queue_after_upload(mock_uploader: SumoUploaderInterface) -> None:
    """Upload queue is always cleared."""
    mock_uploader._queue = [MagicMock(), MagicMock()]
    with patch("fmu.sumo.uploader._upload_files.upload_files"):
        mock_uploader.upload()
    assert mock_uploader._queue == []


def test_upload_with_empty_queue(mock_uploader: SumoUploaderInterface) -> None:
    """Calling uploader with an empty queue works appropriately."""
    mock_result: dict[str, list] = {
        "ok_uploads": [],
        "failed_uploads": [],
        "rejected_uploads": [],
    }
    with patch(
        "fmu.sumo.uploader._upload_files.upload_files", return_value=mock_result
    ) as mock_upload:
        mock_uploader.upload()

    mock_upload.assert_called_once_with(
        [],
        "uuid-1",
        mock_uploader.connection,
        config_path=Path("global_variables.yml"),
    )


def test_from_new_case_registers_case_and_returns_instance() -> None:
    mock_case = MagicMock()
    mock_case.register.return_value = "registered-uuid"

    with (
        patch("fmu.sumo.uploader.SumoConnection"),
        patch("fmu.sumo.uploader.CaseOnDisk", return_value=mock_case),
    ):
        uploader = SumoUploaderInterface.from_new_case(
            case_metadata_path=Path("fmu_case.yml"),
            global_config_path=Path("global_variables.yml"),
        )

    mock_case.register.assert_called_once()
    assert uploader.case_uuid == "registered-uuid"
    assert isinstance(uploader, SumoUploaderInterface)


def test_from_new_case_defaults_env_to_prod_when_env_var_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUMO_ENV", raising=False)

    mock_case = MagicMock()
    mock_case.register.return_value = "uuid"

    with (
        patch("fmu.sumo.uploader.SumoConnection") as mock_conn_cls,
        patch("fmu.sumo.uploader.CaseOnDisk", return_value=mock_case),
    ):
        uploader = SumoUploaderInterface.from_new_case(
            case_metadata_path=Path("fmu_case.yml"),
            global_config_path=Path("global_variables.yml"),
        )

    first_call_args = mock_conn_cls.call_args_list[0]
    assert first_call_args.args[0] == "prod"
    assert uploader.env == "prod"


def test_from_new_case_reads_env_from_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUMO_ENV", "dev")

    mock_case = MagicMock()
    mock_case.register.return_value = "uuid"

    with (
        patch("fmu.sumo.uploader.SumoConnection") as mock_conn_cls,
        patch("fmu.sumo.uploader.CaseOnDisk", return_value=mock_case),
    ):
        uploader = SumoUploaderInterface.from_new_case(
            case_metadata_path=Path("fmu_case.yml"),
            global_config_path=Path("global_variables.yml"),
        )

    first_call_args = mock_conn_cls.call_args_list[0]
    assert first_call_args.args[0] == "dev"
    assert uploader.env == "dev"


def test_from_new_case_explicit_env_overrides_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUMO_ENV", "dev")

    mock_case = MagicMock()
    mock_case.register.return_value = "uuid"

    with (
        patch("fmu.sumo.uploader.SumoConnection") as mock_conn_cls,
        patch("fmu.sumo.uploader.CaseOnDisk", return_value=mock_case),
    ):
        uploader = SumoUploaderInterface.from_new_case(
            case_metadata_path=Path("fmu_case.yml"),
            global_config_path=Path("global_variables.yml"),
            env="prod",
        )

    first_call_args = mock_conn_cls.call_args_list[0]
    assert first_call_args.args[0] == "prod"
    assert uploader.env == "prod"


def test_from_new_case_passes_client_id_to_sumo_connection() -> None:
    mock_case = MagicMock()
    mock_case.register.return_value = "uuid"

    client_id = "custom-uuid"

    with (
        patch("fmu.sumo.uploader.SumoConnection") as mock_conn_cls,
        patch("fmu.sumo.uploader.CaseOnDisk", return_value=mock_case),
    ):
        uploader = SumoUploaderInterface.from_new_case(
            case_metadata_path=Path("fmu_case.yml"),
            global_config_path=Path("global_variables.yml"),
            client_id=client_id,
        )

    first_call_args = mock_conn_cls.call_args_list[0]
    assert first_call_args.kwargs.get("client_id") == client_id
    assert uploader.client_id == client_id


def test_from_new_case_passes_case_metadata_path_to_case_on_disk() -> None:
    mock_case = MagicMock()
    mock_case.register.return_value = "uuid"

    case_metadata_path = Path("fmu_case.yml")

    with (
        patch("fmu.sumo.uploader.SumoConnection"),
        patch("fmu.sumo.uploader.CaseOnDisk", return_value=mock_case) as mock_cod_cls,
    ):
        SumoUploaderInterface.from_new_case(
            case_metadata_path=case_metadata_path,
            global_config_path=Path("global_variables.yml"),
        )

    assert mock_cod_cls.call_args.args[0] == case_metadata_path


def test_from_new_case_stores_global_config_path() -> None:
    mock_case = MagicMock()
    mock_case.register.return_value = "uuid"

    global_config_path = Path("global_variables.yml")

    with (
        patch("fmu.sumo.uploader.SumoConnection"),
        patch("fmu.sumo.uploader.CaseOnDisk", return_value=mock_case),
    ):
        uploader = SumoUploaderInterface.from_new_case(
            case_metadata_path=Path("fmu_case.yml"),
            global_config_path=global_config_path,
        )

    assert uploader.global_config_path == global_config_path
