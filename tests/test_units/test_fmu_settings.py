from pathlib import Path

from fmu.settings import find_nearest_fmu_directory


def test_dot_fmu_data_in_runpath(runpath: Path) -> None:
    """This tests the correctness of two things.

    - The 'runpath' fixture places the .fmu/ directory in the correct place.
    - The current test data within it validates when loaded by the FMU dir class.

    This test should fail if the test data and fmu-settings drift apart.
    """
    fmu_dir = find_nearest_fmu_directory()
    assert fmu_dir.path == (runpath.parent.parent / ".fmu").resolve()
    config = fmu_dir.config.load()

    assert config.masterdata is not None
    assert config.masterdata.smda.field[0].identifier == "DROGON"

    assert config.model is not None
    assert config.model.name == "Drogon"

    assert config.access is not None
    assert config.access.asset.name == "Drogon"
