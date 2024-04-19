from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from fmu.dataio.writers import export_file, export_metadata_file


def test_non_metadata_export_metadata_file():
    with NamedTemporaryFile(buffering=0, suffix=".yaml") as tf, pytest.raises(
        RuntimeError
    ):
        export_metadata_file(Path(tf.name), {}, savefmt="json")

    with NamedTemporaryFile(buffering=0, suffix=".yaml") as tf, pytest.raises(
        RuntimeError
    ):
        export_metadata_file(Path(tf.name), {}, savefmt="yaml")


def test_export_file_raises():
    with NamedTemporaryFile() as tf, pytest.raises(TypeError):
        export_file(
            object(),
            Path(tf.name),
            ".placeholder",
        )
