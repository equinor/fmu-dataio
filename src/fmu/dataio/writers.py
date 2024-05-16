from __future__ import annotations

import json
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Final, Literal

import pandas as pd
import xtgeo
import yaml

from ._logging import null_logger
from ._utils import drop_nones, md5sum
from .readers import FaultRoomSurface

if TYPE_CHECKING:
    from . import types

logger: Final = null_logger(__name__)


def export_metadata_file(
    file: Path,
    metadata: dict,
    savefmt: Literal["yaml", "json"] = "yaml",
) -> None:
    """Export genericly and ordered to the complementary metadata file."""
    if not metadata:
        raise RuntimeError(
            "Export of metadata was requested, but no metadata are present."
        )

    if savefmt == "yaml":
        with open(file, "w", encoding="utf8") as stream:
            stream.write(
                yaml.safe_dump(
                    drop_nones(metadata),
                    allow_unicode=True,
                )
            )
    else:
        with open(file.replace(file.with_suffix(".json")), "w") as stream:
            stream.write(
                json.dumps(
                    drop_nones(metadata),
                    default=str,
                    indent=2,
                    ensure_ascii=False,
                )
            )

    logger.info("Yaml file on: %s", file)


def export_file(
    obj: types.Inferrable,
    filename: Path,
    flag: str | None = None,
) -> str:
    """Export a valid object to file"""

    if isinstance(obj, (Path, str)):
        # special case when processing data which already has metadata
        shutil.copy(obj, filename)
    elif filename.suffix == ".gri" and isinstance(obj, xtgeo.RegularSurface):
        obj.to_file(filename, fformat="irap_binary")
    elif filename.suffix == ".csv" and isinstance(obj, (xtgeo.Polygons, xtgeo.Points)):
        out = obj.copy()  # to not modify incoming instance!
        assert flag is not None
        if "xtgeo" not in flag:
            out.xname = "X"
            out.yname = "Y"
            out.zname = "Z"
            if isinstance(out, xtgeo.Polygons):
                # out.pname = "ID"  not working
                out.get_dataframe(copy=False).rename(
                    columns={out.pname: "ID"}, inplace=True
                )
        out.get_dataframe(copy=False).to_csv(filename, index=False)
    elif filename.suffix == ".pol" and isinstance(obj, (xtgeo.Polygons, xtgeo.Points)):
        obj.to_file(filename)
    elif filename.suffix == ".segy" and isinstance(obj, xtgeo.Cube):
        obj.to_file(filename, fformat="segy")
    elif filename.suffix == ".roff" and isinstance(
        obj, (xtgeo.Grid, xtgeo.GridProperty)
    ):
        obj.to_file(filename, fformat="roff")
    elif filename.suffix == ".csv" and isinstance(obj, pd.DataFrame):
        logger.info(
            "Exporting dataframe to csv. Note: index columns will not be "
            "preserved unless calling 'reset_index()' on the dataframe."
        )
        obj.to_csv(filename, index=False)
    elif filename.suffix == ".arrow":
        from pyarrow import Table

        if isinstance(obj, Table):
            from pyarrow import feather

            # comment taken from equinor/webviz_subsurface/smry2arrow.py
            # Writing here is done through the feather import, but could also be
            # done using pa.RecordBatchFileWriter.write_table() with a few
            # pa.ipc.IpcWriteOptions(). It is convenient to use feather since it
            # has ready configured defaults and the actual file format is the same
            # (https://arrow.apache.org/docs/python/feather.html)

            # Types in pyarrow-stubs package are wrong for the write_feather(...).
            # https://arrow.apache.org/docs/python/generated/pyarrow.feather.write_feather.html#pyarrow.feather.write_feather
            feather.write_feather(obj, dest=str(filename))  # type: ignore
    elif filename.suffix == ".json" and isinstance(obj, FaultRoomSurface):
        with open(filename, "w") as stream:
            json.dump(obj.storage, stream, indent=4)
    elif filename.suffix == ".json":
        with open(filename, "w") as stream:
            json.dump(obj, stream)
    else:
        raise TypeError(f"Exporting {filename.suffix} for {type(obj)} is not supported")

    return str(filename)


def export_file_compute_checksum_md5(
    obj: types.Inferrable,
    filename: Path,
    flag: str | None = None,
) -> str:
    """Export and compute checksum"""
    export_file(obj, filename, flag=flag)
    return md5sum(filename)


def export_temp_file_compute_checksum_md5(
    obj: types.Inferrable, extension: str, flag: str = ""
) -> str:
    """Compute an MD5 sum using a temporary file."""
    if not extension.startswith("."):
        raise ValueError("An extension must start with '.'")

    with NamedTemporaryFile(buffering=0, suffix=extension) as tf:
        logger.info("Compute MD5 sum for tmp file...: %s", tf.name)
        return export_file_compute_checksum_md5(
            obj=obj, filename=Path(tf.name), flag=flag
        )
