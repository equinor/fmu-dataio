import pytest
from fmu.dataio.models.meta import Root
from jsonschema import validate
from jsonschema.exceptions import ValidationError as JSValidationError
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import ValidationError as PDValidationError


class RootFactory(ModelFactory[Root]):
    ...


def pydantic_valid(obj):
    try:
        Root.model_validate(obj)
    except PDValidationError:
        return False
    return True


def json_schema_valid(obj, schema_080):
    try:
        validate(instance=obj, schema=schema_080)
    except JSValidationError:
        return False
    return True


@pytest.mark.parametrize("n", list(range(100)))
def test_pydantic_vs_jsonschema(n, schema_080):
    obj = RootFactory.build().model_dump_json()
    print(obj)
    assert pydantic_valid(obj) == json_schema_valid(obj, schema_080)
