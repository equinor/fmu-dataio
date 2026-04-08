"""Serialization of data objects to files and buffers.

This module handles the i/o exporting data objects. It dispatches to the appropriate
serialization logic based on the underlying object type while checksumming.
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Final

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xtgeo

from fmu.dataio._logging import null_logger
from fmu.dataio._readers import tsurf as tsurf_reader
from fmu.dataio._readers.faultroom import FaultRoomSurface
from fmu.dataio._readers.tsurf import TSurfData
from fmu.dataio._utils import md5sum
from fmu.datamodels.fmu_results.enums import FileFormat

if TYPE_CHECKING:
    from fmu.dataio._metadata.objectdata._base import ObjectData

logger: Final = null_logger(__name__)


def export_object(objdata: ObjectData, file: Path | BytesIO) -> None:
    """Serialize an ObjectData's underlying object to file or buffer.

    Dispatches based on the ObjectData subclass to select the correct serialization
    format.
    """
    obj = objdata.obj

    if isinstance(obj, xtgeo.RegularSurface):
        obj.to_file(file, fformat="irap_binary")

    elif isinstance(obj, (xtgeo.Polygons, xtgeo.Points)):
        _export_tabular_xtgeo(objdata, file)

    elif isinstance(obj, xtgeo.Cube):
        obj.to_file(file, fformat="segy")

    elif isinstance(obj, (xtgeo.Grid, xtgeo.GridProperty)):
        obj.to_file(file, fformat="roff")

    elif isinstance(obj, pd.DataFrame):
        logging.info(
            "Exporting dataframe to csv. Note: index columns will not be preserved "
            "unless calling 'reset_index()' on the dataframe."
        )
        obj.to_csv(file, index=False)

    elif isinstance(obj, pa.Table):
        pq.write_table(obj, where=pa.output_stream(file))

    elif isinstance(obj, FaultRoomSurface):
        _export_json(json.dumps(obj.storage, indent=4), file)

    elif isinstance(obj, TSurfData):
        tsurf_reader.write_tsurf_to_file(obj, file)

    elif isinstance(obj, dict):
        _export_json(json.dumps(obj), file)

    else:
        raise NotImplementedError(
            f"No export support for object type: {type(obj).__name__}"
        )


def _export_tabular_xtgeo(objdata: ObjectData, file: Path | BytesIO) -> None:
    """Export xtgeo Polygons or Points, respecting the configured format."""
    fmt = objdata.fmt

    if fmt == FileFormat.parquet:
        table = pa.Table.from_pandas(objdata.obj_dataframe)
        pq.write_table(table, where=pa.output_stream(file))
    elif fmt == FileFormat.irap_ascii:
        objdata.obj.to_file(file)
    else:
        objdata.obj_dataframe.to_csv(file, index=False)


def _export_json(serialized: str, file: Path | BytesIO) -> None:
    """Write a JSON string to a file path or BytesIO buffer."""
    if isinstance(file, Path):
        with open(file, "w", encoding="utf-8") as stream:
            stream.write(serialized)
    else:
        file.write(serialized.encode("utf-8"))


def compute_md5_and_size(objdata: ObjectData) -> tuple[str, int]:
    """Compute MD5 checksum and size by serializing the object.

    Tries in-memory serialization first, falls back to a temporary file if the in-memory
    approach fails (e.g., for very large objects).
    """
    try:
        return _compute_md5_from_buffer(objdata)
    except Exception as e:
        logger.debug(
            f"Exception {e} occured when trying to compute md5 from memory stream for "
            f"an object of type {type(objdata.obj)}. Will use tempfile instead."
        )
        return _compute_md5_from_tempfile(objdata)


def _compute_md5_from_buffer(objdata: ObjectData) -> tuple[str, int]:
    """Compute MD5 sum and buffer size using in-memory buffer."""
    buffer = BytesIO()
    export_object(objdata, buffer)
    return md5sum(buffer), buffer.getbuffer().nbytes


def _compute_md5_from_tempfile(objdata: ObjectData) -> tuple[str, int]:
    """Compute MD5 sum and file size using a temporary file."""
    with NamedTemporaryFile(buffering=0, suffix=".tmp") as tf:
        path = Path(tf.name)
        export_object(objdata, path)
        return md5sum(path), path.stat().st_size
