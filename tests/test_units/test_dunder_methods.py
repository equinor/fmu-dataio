"""Explicitly test all dunder methods."""

import pytest

from fmu.dataio._model.fields import Parameters
from fmu.dataio._model.global_configuration import Stratigraphy, StratigraphyElement

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
        for item in testdata_stratigraphy:
            count += 1
        assert count == 3
    except Exception:
        assert False, "Stratigraphy class does not have __iter__()"


def test_stratigraphy_dunder_getitem(testdata_stratigraphy):
    try:
        testdata_stratigraphy["TopStratUnit2"]
    except Exception:
        assert False, "Stratigraphy class does not have __getitem__()"


# --------------------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------------------


@pytest.fixture(name="testdata_parameters", scope="function")
def _fixture_testdata_parameters() -> Parameters:
    """
    Return a nested dict of Parameter instances.
    """
    return Parameters(
        root={
            "p1": 42,
            "p2": "not so nested",
            "p3": Parameters(
                root={
                    "p3_1": 42.3,
                    "p3_2": "more nested",
                }
            ),
        }
    )


def test_parameters_dunder_iter(testdata_parameters):
    try:
        count = 0
        for item in testdata_parameters:
            count += 1
        assert count == 3
    except Exception:
        assert False, "Parameters class does not have __iter__()"


def test_parameters_dunder_getitem(testdata_parameters):
    try:
        testdata_parameters["p2"]
    except Exception:
        assert False, "Parameters class does not have __getitem__()"
