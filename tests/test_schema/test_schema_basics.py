"""Test the schema basics."""

import logging
import jsonschema


# pylint: disable=no-member

logger = logging.getLogger(__name__)


def test_schema_basic_json_syntax(all_schemas):
    """Confirm that schemas are valid JSON."""

    for rev, schema in all_schemas.items():
        assert "$schema" in schema, f"$schema not found in {rev}"


def test_schema_example_filenames(metadata_examples):
    """Assert that all examples are .yml, not .yaml"""

    # check that examples are there
    for rev in metadata_examples:
        assert len(metadata_examples[rev]) > 0
        for filename in metadata_examples[rev]:
            assert filename.endswith(".yml"), filename


def test_schema_validate_examples_as_is(all_schemas, metadata_examples):
    """Confirm that examples are valid against the schema"""

    for rev, schema in all_schemas.items():
        for i, (name, metadata) in enumerate(metadata_examples[rev].items()):
            try:
                jsonschema.validate(instance=metadata, schema=schema)
            except jsonschema.exceptions.ValidationError:
                logger.error("Failed validating existing example: %s", name)
                logger.error("Schema revision was %s", rev)
                if i == 0:
                    logger.error(
                        "This was the first example attempted."
                        "Error is most likely int he schema."
                    )
                else:
                    logger.error(
                        "This was not the first example attemted."
                        "Error is most likely in the example."
                    )
                raise
