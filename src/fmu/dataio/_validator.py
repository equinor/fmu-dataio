"""Module for DataIO _Validator

Contains the _Validator class.

"""

import logging
import urllib

from pathlib import Path
from typing import Union

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

    def __init__(
        self, global_schema: Union[dict, str, Path] = None, verbosity: str = "CRITICAL"
    ):
        """Initialize the _Validator.

        Args:
            global_schema (dict | str | Path) (optional): A reference to a valid JSON
            schema or a valid JSON schema. If provided, all validation will be done
            using this schema. If not provided, schema must be given directly to the
            validate method or parsed from reference in the metadata instance (default).
        """
        self.verbosity = verbosity
        logger.setLevel(level=self.verbosity)
        logger.info("Verbosity is %s ", self.verbosity)

        self._cached_schema = {"reference": None, "schema": None}

        self._global_schema = self._parse_schema(global_schema)

        logger.info("_Validator is initialized.")

    # ==================================================================================
    # Main methods
    # ==================================================================================

    def validate(
        self,
        filename: Union[str, Path],
        schema_reference: Union[str, Path, dict] = None,
    ):
        """Validate the metadata associated with the filename.

        If a global_schema is given to the class, this schema will be used. If this is
        not given, we use the schema given to this method. If this is not given, we use
        the schema referenced in the metadata instance.

        However, we want to avoid parsing the same schema many times, e.g. in the case
        of validating 1000 files referencing the same schema. So we cache it, and only
        parse again if the reference changes.

        Args:
            filename (str | Path): Filename of file to be evaluated.
            schema_reference (str | Path | dict) (optional): Schema to use for this
            specific file. If not provided, global schema from class or schema
            referenced in the metadata will be used.

        Returns:
            dict: The validation results.
        """

        logger.setLevel(level=self.verbosity)
        logger.info("Validating file: %s", filename)

        if self._is_metadata_file(filename):
            with open(filename, "r") as stream:
                instance = yaml.safe_load(stream)
        else:
            instance = read_metadata(filename)

        # pre-flight validation to check basics
        preflight_valid, preflight_reason = self._preflight_validation(instance)
        if preflight_valid is False:
            return self._create_results(preflight_valid, preflight_reason)

        if schema_reference is not None:
            logger.info("Local schema has been given, parsing it.")
            use_schema = self._parse_schema(schema_reference)
            if self._global_schema is not None:
                logger.info("Both global and local schema has been given. Using local.")
        elif self._global_schema is not None:
            logger.info("We have a global schema, and will use that.")
            use_schema = self._global_schema
        else:
            logger.info("No global schema, no local schema.")
            use_schema = self._parse_schema(instance["$schema"])

        return self._validate(instance, use_schema)

    # ==================================================================================
    # Private methods
    # ==================================================================================

    def _is_metadata_file(self, filename):
        """Check if given filename is a metadata file.

        We want to detect if a reference is given to a metadata file directly, or to
        a data file.

        """
        fname = Path(filename)
        if fname.stem.startswith(".") and str(fname).endswith((".yml", ".yaml")):
            return True
        return False

    def _preflight_validation(self, instance):
        """Do preflight validation of a metadata instance.

        Confirm that elements required for the actual validation is present and
        correctly formatted.
        """

        if "$schema" not in instance:
            reason = "$schema is a required property."
            return False, reason

        return True, None

    def _parse_schema(self, schema_ref: Union[str, Path, dict]):
        """Parse the schema from a reference.

        If schema is cached, return it.
        Detect if schema_reference is a dict, a url or a path, and parse it.

        Args:
            schema_ref (str | Path | dict): Reference to a valid JSON schema

        Returns:
            dict: The parsed schema.
        """

        if schema_ref is None:
            logger.info("_parse_schema was called with no schema_ref")
            return None

        if isinstance(schema_ref, dict):
            logger.info("Schema given as a dict, use directly.")
            _schema = schema_ref
            self._cached_schema = {"reference": None, "schema": _schema}
            return schema_ref

        logger.info("Parse schema from reference: %s", schema_ref)

        if schema_ref == self._cached_schema["reference"]:
            logger.info("Returning cached schema.")
            return self._cached_schema["schema"]

        if isinstance(schema_ref, str) and schema_ref.startswith("http"):
            logger.info("Schema_reference is a URL")
            _schema = self._parse_schema_from_url(schema_url=schema_ref)
        else:
            logger.info("Final fallback: Schema must be a file path")
            _schema = self._parse_schema_from_file(schema_path=schema_ref)

        # write to cache before returning
        self._cached_schema = {"reference": schema_ref, "schema": _schema}
        return _schema

    def _parse_schema_from_file(self, schema_path):
        """Parse schema from file, return dict."""

        logger.info("Fetching schema from %s", schema_path)

        with open(schema_path, "r", encoding="utf-8") as stream:
            schema = json.load(stream)
        return schema

    def _parse_schema_from_url(self, schema_url):
        """Parse schema from a url, return dict."""

        logger.info("Fetching schema from %s", schema_url)

        with urllib.request.urlopen(schema_url) as response:
            schema = json.load(response)

        return schema

    def _validate(self, instance, schema):
        """Validate the instance on the schema."""

        try:
            jsonschema.validate(instance=instance, schema=schema)
            logger.info("Validation succeeded, returning results.")
            return self._create_results(True)
        except jsonschema.exceptions.ValidationError as err:
            logger.info("Validation failed, returning results.")
            return self._create_results(False, err.message)
        except jsonschema.exceptions.SchemaError as err:
            raise err

    def _create_results(self, valid: bool, reason: str = None):
        """Correctly format the validation results."""
        return {"valid": valid, "reason": reason}
