"""Test the utils module"""

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from fmu.datamodels.common.access import Access
from fmu.datamodels.common.tracklog import Tracklog
from fmu.datamodels.fmu_results import fields

from fmu.dataio._export import export_metadata_file
from fmu.dataio._utils import md5sum

from ..utils import _get_pydantic_models_from_annotation


@pytest.mark.parametrize(
    "content, checksum",
    [
        (b"", "1B2M2Y8AsgTpgAmY7PhCfg=="),
        (b"hello", "XUFAKrxLKna5cZ2REBfFkg=="),
    ],
)
def test_md5sum_base64(tmp_path: Path, content: bytes, checksum: str) -> None:
    """Files and buffers produce the known base64 MD5 checksum."""
    path = tmp_path / "data.bin"
    path.write_bytes(content)
    buffer = BytesIO(content)
    buffer.seek(0, 2)

    assert md5sum(path) == checksum
    assert md5sum(buffer) == checksum


def test_non_metadata_export_metadata_file() -> None:
    with (
        NamedTemporaryFile(buffering=0, suffix=".yaml") as tf,
        pytest.raises(RuntimeError),
    ):
        export_metadata_file(Path(tf.name), {})


def test_get_pydantic_models_from_annotation() -> None:
    annotation = list[Access] | fields.File
    assert _get_pydantic_models_from_annotation(annotation) == [
        Access,
        fields.File,
    ]
    annotation = dict[str, Access] | list[fields.File] | None
    assert _get_pydantic_models_from_annotation(annotation) == [
        Access,
        fields.File,
    ]

    annotation = list[Access | fields.File | Tracklog]
    assert _get_pydantic_models_from_annotation(annotation) == [
        Access,
        fields.File,
        Tracklog,
    ]

    annotation = list[list[list[list[Tracklog]]]]
    assert _get_pydantic_models_from_annotation(annotation) == [Tracklog]

    annotation = str | list[int] | dict[str, int]
    assert not _get_pydantic_models_from_annotation(annotation)
