from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Self, TypedDict

import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from fmu.sumo.uploader._fileonjob import FileOnJob

# Client id for Sumo uploader to identify the source of uploads
SUMO_CLIENT_ID: Final[str] = "a65dc4cc-3dec-43df-9599-e66d3abc4dca"


def pa_table_to_bytes(table: pa.Table) -> bytes:
    """Converts a PyArrow table to a bytestring."""
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    return sink.getvalue().to_pybytes()


class SumoUploadResult(TypedDict):
    ok_uploads: list[Any]
    failed_uploads: list[Any]
    rejected_uploads: list[Any]


class SumoUploaderInterface:
    """An interface for uploading to Sumo."""

    def __init__(
        self,
        env: str,
        case_uuid: str,
        global_config_path: Path,
        *,
        client_id: str = SUMO_CLIENT_ID,
    ) -> None:
        from fmu.sumo.uploader import SumoConnection

        self.env = env
        self.case_uuid = case_uuid
        self.client_id = client_id
        self.global_config_path = global_config_path

        self.connection = SumoConnection(
            self.env, case_uuid=self.case_uuid, client_id=self.client_id
        )

        self._queue: list[FileOnJob] = []

    def _queue_file(self, file: FileOnJob, metadata: dict[str, Any]) -> None:
        """Sets additional values before queueing a file for uploader."""
        file.path = metadata["file"]["relative_path"]
        file.metadata_path = ""
        file.size = len(file.byte_string)

        self._queue.append(file)

    def queue_table(self, table: pa.Table, metadata: dict[str, Any]) -> None:
        """Stage a table for upload."""
        from fmu.sumo.uploader._fileonjob import FileOnJob

        table_bytes = pa_table_to_bytes(table)
        file = FileOnJob(table_bytes, metadata)
        self._queue_file(file, metadata)

    def upload(self) -> SumoUploadResult:
        """Uploads all queued files to Sumo.

        Returns:
            Number of files succeeded/failed during upload.
        """
        from fmu.sumo.uploader._upload_files import upload_files

        result = upload_files(
            list(self._queue),  # Copy so we don't clear for uploader's executors
            self.case_uuid,
            self.connection,
            config_path=self.global_config_path,
        )
        self._queue.clear()
        return result

    @classmethod
    def from_new_case(
        cls,
        case_metadata_path: Path,
        global_config_path: Path,
        *,
        env: str | None = None,
        client_id: str = SUMO_CLIENT_ID,
    ) -> Self:
        """Registers a case on Sumo by sending the case metadata"""
        from fmu.sumo.uploader import CaseOnDisk, SumoConnection

        _env = env or os.environ.get("SUMO_ENV", "prod")
        register_connection = SumoConnection(_env, client_id=client_id)

        case = CaseOnDisk(case_metadata_path, register_connection)
        case_uuid = case.register()

        return cls(_env, case_uuid, global_config_path, client_id=client_id)
