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


def test_access_classification_logic():
    """Test various inputs of access.ssdl and access.classification."""

    # check that ssdl.access_level is mirrored to classification
    assert (
        global_configuration.Access.model_validate(
            {
                "asset": {"name": "FakeName"},
                "ssdl": {"access_level": "internal"},
            }
        ).classification
        == "internal"
    )
    assert (
        global_configuration.Access.model_validate(
            {
                "asset": {"name": "FakeName"},
                "ssdl": {"access_level": "restricted"},
            }
        ).classification
        == "restricted"
    )
    # classification together with ssdl.access_level should warn
    # and ignore the ssdl_access level
    with pytest.warns(match="The config contains both"):
        assert (
            global_configuration.Access.model_validate(
                {
                    "asset": {"name": "FakeName"},
                    "ssdl": {"access_level": "internal"},
                    "classification": "restricted",
                }
            ).classification
            == "restricted"
        )
    # classification together with ssdl.rep_include is ok
    global_configuration.Access.model_validate(
        {
            "asset": {"name": "FakeName"},
            "ssdl": {"rep_include": True},
            "classification": "internal",
        }
    )
    # ssdl is optional as long as classification is present
    global_configuration.Access.model_validate(
        {
            "asset": {"name": "FakeName"},
            "classification": "internal",
        }
    )
    # missing classification and ssdl.access_level should fail
    with pytest.raises(ValueError, match="Please provide access.classification"):
        global_configuration.Access.model_validate(
            {
                "asset": {"name": "FakeName"},
                "ssdl": {"rep_include": False},
            }
        )
