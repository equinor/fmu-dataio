from io import StringIO

import pytest
import yaml
from fmu.dataio.datastructure.configuration import global_configuration
from hypothesis import given, strategies
from pydantic import ValidationError


@given(
    name=strategies.text(min_size=1),
    stratigraphic=strategies.booleans(),
    alias=strategies.lists(
        strategies.one_of(
            strategies.text(),
            strategies.none(),
        )
    ),
    stratigraphic_alias=strategies.lists(
        strategies.one_of(
            strategies.text(),
            strategies.none(),
        )
    ),
)
def test_drop_none(name, stratigraphic, alias, stratigraphic_alias):
    cnf = global_configuration.StratigraphyElement(
        name=name,
        stratigraphic=stratigraphic,
        alias=alias,
        stratigraphic_alias=stratigraphic_alias,
    )
    if cnf.alias is not None:
        assert all(v is not None for v in cnf.alias)

    if cnf.stratigraphic_alias is not None:
        assert all(v is not None for v in cnf.stratigraphic_alias)


def test_access_classification_mirrors():
    # Tests the _classification_mirros_accesslevel(...)
    # model_validator.
    global_configuration.Access.model_validate(
        {
            "asset": {"name": "FakeName"},
            "ssdl": {"access_level": "internal"},
        }
    ).classification == "internal"

    global_configuration.Access.model_validate(
        {
            "asset": {"name": "FakeName"},
            "ssdl": {"access_level": "restricted"},
        }
    ).classification == "restricted"

    # classification should be set to restricted if
    # ssdl.access_level => asset
    global_configuration.Access.model_validate(
        {
            "asset": {"name": "FakeName"},
            "ssdl": {"access_level": "asset"},
        }
    ).classification == "restricted"


@pytest.mark.parametrize(
    "obj",
    (
        StringIO(
            """MSL:
  stratigraphic: false
  name: MSL
Seabase:
  stratigraphic: false
  name: Seabase
TopVolantis:
  stratigraphic: true
  name: VOLANTIS GP. Top
  alias:
  stratigraphic_alias:
    - TopValysar
    - Valysar Fm. Top
"""
        ),
        StringIO(
            """HorName:
  name: Proper Name
  alias:
  stratigraphic: true
"""
        ),
        StringIO(
            """HorName:
  name: Proper Name
  stratigraphic_alias:
  stratigraphic: true
"""
        ),
    ),
)
def test_illformed_stratigraphic(obj: StringIO):
    with pytest.raises(ValidationError):
        print(global_configuration.Stratigraphy.model_validate(yaml.safe_load(obj)))
