"""Explicitly test all dunder methods."""

import pytest

from fmu.dataio._models.fmu_results.global_configuration import (
    Stratigraphy,
    StratigraphyElement,
)

# --------------------------------------------------------------------------------------
# Stratigraphy
# --------------------------------------------------------------------------------------


@pytest.fixture(name="testdata_stratigraphy", scope="function")
def _fixture_testdata_stratigraphy() -> Stratigraphy:
    """
    Return a dict of StratigraphyElement instances.
    """
    return Stratigraphy(
        root={
            "TopStratUnit1": StratigraphyElement(
                name="Stratigraphic Unit 1",
                stratigraphic=True,
                alias=["TopSU1", "TopLayer1"],
            ),
            "TopStratUnit2": StratigraphyElement(
                name="Stratigraphic Unit 2",
                stratigraphic=True,
                alias=["TopSU2", "TopLayer2"],
            ),
            "TopStratUnit3": StratigraphyElement(
                name="Stratigraphic Unit 3",
                stratigraphic=True,
                alias=["TopSU3", "TopLayer3"],
            ),
        }
    )


def test_stratigraphy_dunder_iter(testdata_stratigraphy):
    try:
        count = 0
        for _ in testdata_stratigraphy:
            count += 1
        assert count == 3
    except Exception:
        pytest.fail("Stratigraphy class does not have __iter__()")


def test_stratigraphy_dunder_getitem(testdata_stratigraphy):
    try:
        testdata_stratigraphy["TopStratUnit2"]
    except Exception:
        pytest.fail("Stratigraphy class does not have __getitem__()")
