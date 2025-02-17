from __future__ import annotations

import json
from typing import Any

import pytest
from pytest import MonkeyPatch

from fmu.dataio._models import schemas
from fmu.dataio._models._schema_base import FmuSchemas, SchemaBase


def contains_discriminator_mapping(schema: Any) -> bool:
    """Recursively checks ["discriminator"]["mapping"] in the schema."""
    if isinstance(schema, dict):
        if (
            "discriminator" in schema and isinstance(schema["discriminator"], dict)
        ) and "mapping" in schema["discriminator"]:
            return True
        for value in schema.values():
            if contains_discriminator_mapping(value):
                return True
    elif isinstance(schema, list):
        for item in schema:
            if contains_discriminator_mapping(item):
                return True
    return False


@pytest.mark.parametrize("schema", schemas)
def test_schemas_uptodate(schema: SchemaBase) -> None:
    """
    Test to verify if the local schemas are up to date with the schema
    generated by pydantic's `dump` method. It compares the content of
    the local schema with the output of `dump()`.

    To get more feedback or generate new schemas run:

        ./tools/update_schema --diff

    If you are generating a production release try running:

        ./tools/update_schema --diff --prod
    """
    with open(schema.PATH) as f:
        assert json.load(f) == schema.dump()


@pytest.mark.parametrize("schema", schemas)
def test_schema_url_changes_with_env_var(
    schema: SchemaBase, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("DEV_SCHEMA", "")
    json = schema.dump()
    assert schema.url().startswith(FmuSchemas.PROD_URL)
    assert json["$id"].startswith(FmuSchemas.PROD_URL)
    assert json["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    monkeypatch.setenv("DEV_SCHEMA", "1")
    json = schema.dump()
    assert schema.url().startswith(FmuSchemas.DEV_URL)
    assert json["$id"].startswith(FmuSchemas.DEV_URL)
    assert json["$schema"] == "https://json-schema.org/draft/2020-12/schema"


@pytest.mark.parametrize("schema", schemas)
def test_no_discriminator_mappings_leftover_in_schema(schema: SchemaBase) -> None:
    """Sumo's AJV validator doesn't like discriminator mappings leftover in the
    schema."""
    with open(schema.PATH) as f:
        schema = json.load(f)
    assert contains_discriminator_mapping(schema) is False
