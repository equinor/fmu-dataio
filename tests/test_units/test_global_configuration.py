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
    global_configuration.Access.model_validate(
        {
            "asset": {"name": "FakeName"},
            "ssdl": {"access_level": "asset"},
        }
    ).classification == "restricted"
