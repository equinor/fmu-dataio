"""Module for DataIO _Validator

This contains validation functionality for FMU metadata.

"""

import logging
import requests

from pathlib import Path
from typing import Optional, Union

from fmu.dataio import read_metadata

import yaml
import json
import jsonschema

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


class _Validator:
    """Class for validating metadata.

    This is a private class for fmu.dataio. The intention is that a public function in
    fmu-dataio is to be facing the user.

    """

    def __init__(self, schema: Union[dict, str, Path] = None):
        """Initialize the _Validator.

        Args:
            schema (dict | str | Path) (optional): A reference to a valid JSON schema or
            a valid JSON schema. Default: None, which will prompt usage of the schema
            referenced in the metadata.

        """

        if schema is not None:
            self.schema = self._parse_schema(schema)
        else:
            self.schema = schema

        self._schema_reference = None

        logger.info("_Validator is initialized.")

    # ==================================================================================
    # Main methods
    # ==================================================================================

    def validate(self, filename):
        """Validate the metadata associated with the filename.

        Args:
            metadata (dict or filename): The metadata to be validated, given as either a
            dictionary or a filename to either data file or associated metadata file.

        Returns:
            dict: The validation results.
        """

        instance = read_metadata(filename)

        if self.schema is None:
            logger.info("Schema is not given, getting from metadata.")
            logger.info("Schema reference is %s", self.schema_reference)
            if self.schema_reference != instance["$schema"]:
                logger.info("Schema reference is different from existing, parsing.")
                self.schema_reference = instance["$schema"]
                logger.info("Schema reference now set to %s", self.schema_reference)
                self.schema = self._parse_schema_from_url(self._schema_reference)
            else:
                logger.info("Schema reference is same as existing, re-using.")
                self.schema_reference = self._get_schema_reference(instance)

        return self._validate(instance, self.schema)

    # ==================================================================================
    # Private methods
    # ==================================================================================

    def _parse_schema(self, schema_ref):
        """Parse the schema from a reference.

        Detect if schema_reference is a dict, a url or a path, and parse it.

        Returns:
            dict: The parsed schema.
        """

        if isinstance(schema_ref, dict):
            logger.info("Schema given as a dict, use directly.")
            return schema_ref
        if isinstance(schema_ref, str) and schema_ref.startswith("http"):
            logger.info("schema_reference is a URL")
            return self._parse_schema_from_url(schema_url=schema_ref)
        else:
            return self._parse_schema_from_file(schema_path=schema_ref)

    def _parse_schema_from_file(self, schema_path):
        """Parse schema from file, return dict."""

        with open(schema_path, "r", encoding="utf-8") as stream:
            schema = json.load(stream)
        return schema

    def _parse_schema_from_url(self, schema_url):
        """Parse schema from a url, return dict."""
