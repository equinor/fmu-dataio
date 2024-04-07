import pytest
from fmu.dataio.datastructure.configuration import global_configuration
from hypothesis import given, strategies


@given(
    name=strategies.text(min_size=1),
    stratigraphic=strategies.booleans(),
    alias=strategies.one_of(
        strategies.none(),
        strategies.lists(strategies.one_of(strategies.text(), strategies.none())),
    ),
    stratigraphic_alias=strategies.one_of(
        strategies.none(),
        strategies.lists(strategies.one_of(strategies.text(), strategies.none())),
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
    gc = global_configuration.Access.model_validate(
        {
            "asset": {"name": "FakeName"},
            "ssdl": {"access_level": "asset"},
        }
    )
    assert gc.classification == "restricted"
    assert gc.ssdl.access_level == "restricted"


def test_parse(globalconfig1):
    """Test the parse method."""

    # runs when config is not given
    # global_configuration.parse(None)

    # runs when config is empty
    global_configuration.parse({})

    # crashes when config is not a dict
    with pytest.raises(ValueError):
        global_configuration.parse("a string")

    # keeps only the wanted keys
    assert "masterdata" in globalconfig1
    globalconfig1["not_used"] = {"not-used": "not-used"}
    assert "not_used" in globalconfig1
    result = global_configuration.parse(globalconfig1)
    assert "masterdata" in result
    assert "not_used" not in result
    del globalconfig1["not_used"]
